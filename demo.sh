#!/bin/bash
# Doris HA demo on GCP — repeatable lifecycle: up → monitor → break → restore → measure → down
#
#   ./demo.sh up            terraform apply (4 VMs + firewall) -> ansible (Doris, cluster, probes) -> seed data (idempotent)
#   ./demo.sh status        FE / BE / replica view, who is master
#   ./demo.sh client        re-run only the probe-client role (ansible --limit client)
#   ./demo.sh plan          terraform plan + ansible --check --diff (what would change)
#   ./demo.sh monitor [--fresh] [--order master-first|follower-first]  start the three probes (--fresh restarts them with empty logs) (mysql / jdbc / arrow-flight, 1 op/s INSERT>UPSERT>SELECT>DELETE>SELECT) on the client VM and tail them live
#   ./demo.sh break [--target fe|be|vm] [--mode crash|dead|hang|stop] [--on master|follower|<vm>]
#                           inject a fault (default: stop the VM holding the FE master); repeat to stack faults
#   ./demo.sh restore       reverse every recorded fault (newest first) and wait until the cluster is healthy
#   ./demo.sh measure [--label X] [--json]  pull the three probe logs; outage windows, failed ops, availability level; --label copies logs to logs/
#   ./demo.sh stop|start    terraform apply vm_status=TERMINATED|RUNNING (keeps disks; FE/BE auto-start via systemd)
#   ./demo.sh down          terraform destroy: VMs + firewall (asks for confirmation)
#   ./demo.sh auto [--keep] up → monitor → break → restore → measure → down  (--keep skips down)
#   any command + --dry-run  print the gcloud/ssh commands instead of running them
set -euo pipefail

# ============================== settings ======================================
PROJECT=doris-poc
REGION=asia-east1
ZONES=(a b c)                       # one VM per zone
MACHINE=e2-standard-4
DISK_GB=50
DORIS_VERSION=4.1.1
PRIORITY_NET=10.140.0.0/24          # subnet of the default VPC in $REGION
FW_RULE=doris-client-from-me        # firewall rule for 9030/8030/8040 from ALLOW_IP
ALLOW_IP="${ALLOW_IP:-}"            # empty = detect current public IP
NAME_PREFIX=doris
PROBE_SECS=${PROBE_SECS:-900}       # how long a probe runs in monitor/auto
AUTO_BASELINE=${AUTO_BASELINE:-30}  # auto: seconds of probe before break
AUTO_OUTAGE=${AUTO_OUTAGE:-90}      # auto: seconds to keep the node down
CLIENT_VM=doris-client              # 4th VM inside the VPC running the three probes (mysql / jdbc / arrow-flight)
CLIENT_ZONE=${REGION}-a
CLIENT_MACHINE=e2-small
PROBES=(mysql jdbc flight)
# ==============================================================================

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HERE/.state"; mkdir -p "$STATE"
HOSTS="$STATE/hosts.tsv"; PROBES_ON="$STATE/probes_on"; FAULTS="$STATE/faults"
PY="$HERE/venv/bin/python"
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
DRY=0; KEEP=0; YES=0
ARGS=()
OPT_TARGET=vm; OPT_MODE=""; OPT_ON=master; OPT_ORDER=""; OPT_LABEL=""; OPT_JSON=0; OPT_FRESH=0
while [ $# -gt 0 ]; do case "$1" in
  --dry-run) DRY=1;; --keep) KEEP=1;; --yes|-y) YES=1;; --json) OPT_JSON=1;;
  --fresh) OPT_FRESH=1;; --target) OPT_TARGET=$2; shift;; --mode) OPT_MODE=$2; shift;; --on) OPT_ON=$2; shift;; --order) OPT_ORDER=$2; shift;; --label) OPT_LABEL=$2; shift;;
  *) ARGS+=("$1");; esac; shift; done
CMD="${ARGS[0]:-help}"

# ------------------------------ helpers ---------------------------------------
c_hdr(){ printf '\n\033[1;36m== %s ==\033[0m  \033[2m%s\033[0m\n' "$1" "$(date +%T)"; }
c_ok(){ printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
c_warn(){ printf '\033[1;33m! %s\033[0m\n' "$*"; }
event(){ printf '\033[1;35m▶ EVENT %s\033[0m\n' "$*"; [ $DRY = 0 ] && [ -f "$PROBES_ON" ] && ssh_node "$CLIENT_VM" "for f in /opt/probe/log/*.log; do [ -f \$f ] && echo \"\$(date +%T) EVENT $*\" >> \$f; done" || true; }
run(){ if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m %s\n' "$*"; else "$@"; fi; }
gc(){ run gcloud "$@" --project="$PROJECT" --quiet; }
vm_name(){ echo "${NAME_PREFIX}-$1"; }               # index 1..N
vm_zone(){ echo "${REGION}-${ZONES[$(( $1 - 1 ))]}"; }
N=${#ZONES[@]}
ssh_node(){ # ssh_node <vm> <cmd...>
  local vm=$1; shift; local z; z=$(zone_of "$vm")
  if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m gcloud compute ssh %s --zone=%s --command=\x27%s\x27\n' "$vm" "$z" "$*"; return; fi
  gcloud compute ssh "$vm" --project="$PROJECT" --zone="$z" --quiet --strict-host-key-checking=no --command="$*" 2>/dev/null
}
scp_from(){ local vm=$1 src=$2 dst=$3; local z; z=$(zone_of "$vm")   # download <vm>:<src> to local <dst>
  if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m gcloud compute scp %s:%s %s --zone=%s\n' "$vm" "$src" "$dst" "$z"; return; fi
  gcloud compute scp "$vm:$src" "$dst" --project="$PROJECT" --zone="$z" --quiet --strict-host-key-checking=no 2>/dev/null
}
scp_node(){ local vm=$1 src=$2 dst=$3; local z; z=$(zone_of "$vm")
  if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m gcloud compute scp %s %s:%s --zone=%s\n' "$src" "$vm" "$dst" "$z"; return; fi
  gcloud compute scp --recurse "$src" "$vm:$dst" --project="$PROJECT" --zone="$z" --quiet --strict-host-key-checking=no 2>/dev/null
}
zone_of(){ [ "$1" = "$CLIENT_VM" ] && { echo "$CLIENT_ZONE"; return; }; local i; for i in $(seq 1 $N); do [ "$(vm_name $i)" = "$1" ] && vm_zone $i && return; done; echo "?"; }
py(){ if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m cluster.py %s\n' "$*"; else "$PY" "$HERE/cluster.py" "$@"; fi; }
need_hosts(){ [ -s "$HOSTS" ] || refresh_hosts; }

refresh_hosts(){ # write name/zone/internal/external of every VM to hosts.tsv
  [ $DRY = 1 ] && { echo "[dry-run] refresh $HOSTS from gcloud compute instances list"; return; }
  gcloud compute instances list --project="$PROJECT" --filter="name~^${NAME_PREFIX}-[0-9]+$" \
    --format="value(name,zone.basename(),networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs[0].natIP)" \
    | sort > "$HOSTS"
  printf '  %-8s %-14s %-12s %s\n' NAME ZONE INTERNAL EXTERNAL; sed 's/\t/ /g' "$HOSTS" | awk '{printf "  %-8s %-14s %-12s %s\n",$1,$2,$3,$4}'
}
my_ip(){ [ -n "$ALLOW_IP" ] && echo "$ALLOW_IP" || curl -s -4 ifconfig.me; }
ensure_venv(){ [ -x "$PY" ] || { python3 -m venv "$HERE/venv" && "$HERE/venv/bin/pip" -q install pymysql ansible-core; }; [ -x "$HERE/venv/bin/ansible-playbook" ] || "$HERE/venv/bin/pip" -q install ansible-core; }
tf(){ if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m infra/tf.sh %s\n' "$*"; else ALLOW_IP="$(my_ip)" "$HERE/infra/tf.sh" "$@"; fi; }
ansible_play(){ # ansible_play <extra args...>  (stdin/stderr redirected: ansible refuses non-blocking handles)
  ensure_venv
  if [ $DRY = 1 ]; then printf '\033[2m[dry-run]\033[0m ansible-playbook site.yml %s\n' "$*"; return; fi
  ( cd "$HERE/ansible" && "$HERE/venv/bin/ansible-playbook" site.yml "$@" < /dev/null 2>&1 | cat )
}
probe_running(){ [ -f "$PROBES_ON" ]; }
wait_ssh(){ [ $DRY = 1 ] && return; local i; for i in $(seq 1 18); do ssh_node "$1" "true" 2>/dev/null && return; sleep 10; done; c_warn "$1: ssh not reachable"; return 1; }
vm_status(){ gcloud compute instances describe "$1" --project="$PROJECT" --zone="$(zone_of "$1")" --format="value(status)" 2>/dev/null || echo "ABSENT"; }
ensure_client_vm(){ c_hdr "client: ansible --limit client"; wait_ssh "$CLIENT_VM"; ansible_play --limit client; c_ok "client VM ready (probes: ${PROBES[*]})"; }

# ------------------------------ commands --------------------------------------
cmd_up(){
  c_hdr "up: terraform apply (4 VMs, firewall, APIs, inventory)"
  tf_power RUNNING
  tf apply -input=false -auto-approve -var vm_status=RUNNING   # 2nd pass: external IPs assigned at power-on -> inventory
  refresh_hosts
  c_hdr "up: ansible (Doris nodes -> cluster -> probe client)"
  for i in $(seq 1 $N); do wait_ssh "$(vm_name $i)" & done; wait_ssh "$CLIENT_VM" & wait
  ansible_play
  ensure_venv
  py wait "$HOSTS" 300
  c_hdr "up: seed data"
  py seed "$HOSTS" 10000
  py status "$HOSTS"
  c_ok "cluster ready"
}

cmd_plan(){ c_hdr "plan: terraform"; tf plan -input=false -var vm_status=RUNNING; c_hdr "plan: ansible --check --diff"; ansible_play --check --diff; }

cmd_status(){ need_hosts; py alive "$HOSTS" || true; if [ -s "$FAULTS" ]; then echo "active faults (.state/faults):"; sed 's/^/  /' "$FAULTS"; fi; py status "$HOSTS" || true; }

cmd_monitor(){
  need_hosts; ensure_venv
  if probe_running && [ $OPT_FRESH = 0 ]; then c_warn "probes already running on $CLIENT_VM, tailing them (use --fresh to restart with empty logs)"; else
    py seed "$HOSTS" 10000     # table must exist with the probes' schema
    if [ $DRY = 1 ]; then :; elif [ -n "$OPT_ORDER" ]; then      # --order master-first|follower-first: which FE the clients land on
      local m; m=$(py resolve "$HOSTS" master)
      { [ "$OPT_ORDER" = master-first ] && awk -F'\t' -v m="$m" '$1==m{print $1" "$3}' "$HOSTS"
        awk -F'\t' -v m="$m" '$1!=m{print $1" "$3}' "$HOSTS"
        [ "$OPT_ORDER" = follower-first ] && awk -F'\t' -v m="$m" '$1==m{print $1" "$3}' "$HOSTS"; } > "$STATE/client-hosts"
    else awk -F'\t' '{print $1" "$3}' "$HOSTS" > "$STATE/client-hosts"; fi     # name + INTERNAL ip
    scp_node "$CLIENT_VM" "$STATE/client-hosts" /opt/probe/hosts
    ssh_node "$CLIENT_VM" "rm -f /opt/probe/log/*.log; sudo systemctl restart probe-mysql probe-jdbc probe-flight; sleep 2; systemctl is-active probe-mysql probe-jdbc probe-flight | tr '\\n' ' '; echo"
    [ $DRY = 1 ] || touch "$PROBES_ON"
    c_ok "probes started on $CLIENT_VM: ${PROBES[*]} (logs /opt/probe/log/*.log)"
  fi
  [ "${MONITOR_BG:-0}" = 1 ] && return
  echo "  (Ctrl-C leaves the screen; the probes keep running on $CLIENT_VM)"
  ssh_node "$CLIENT_VM" "tail -n 5 -F /opt/probe/log/mysql.log | sed -u 's/^/[mysql ] /' & tail -n 5 -F /opt/probe/log/jdbc.log | sed -u 's/^/[jdbc  ] /' & tail -n 5 -F /opt/probe/log/flight.log | sed -u 's/^/[flight] /' & wait"
}

probe_tail(){ [ $DRY = 1 ] || ssh_node "$CLIENT_VM" "for p in mysql jdbc flight; do echo \"--- \$p\"; tail -n ${1:-4} /opt/probe/log/\$p.log; done"; }

fault_add(){ [ $DRY = 1 ] || echo "$(date +%T) $1 $2 $3" >> "$FAULTS"; }
# FE pattern uses a [D] regex trick so pkill -f never matches the ssh shell that carries the command itself
proc_pattern(){ [ "$1" = fe ] && echo "-f org.apache.doris.[D]orisFE" || echo "-x doris_be"; }
unit_of(){ [ "$1" = fe ] && echo doris-fe || echo doris-be; }

cmd_break(){ # --target fe|be|vm --mode crash|dead|hang|stop --on master|follower|<vm>
  need_hosts
  local target=$OPT_TARGET mode=$OPT_MODE on=$OPT_ON
  [ -z "$mode" ] && { [ "$target" = vm ] && mode=stop || mode=crash; }
  case "$target/$mode" in vm/stop|fe/crash|fe/dead|fe/hang|be/crash|be/dead|be/hang) ;; *) c_warn "unsupported --target $target --mode $mode"; exit 2;; esac
  local vm role; vm=$( [ $DRY = 1 ] && echo "<$on>" || py resolve "$HOSTS" "$on"); role=$( [ $DRY = 1 ] && echo "FE ?" || py role "$HOSTS" "$vm")
  c_hdr "break: $target $mode on $vm ($role)"
  event "break: $target $mode on $vm ($role)"
  fault_add "$target" "$mode" "$vm"
  case "$target/$mode" in
    vm/stop)  gc compute instances stop "$vm" --zone="$(zone_of "$vm")"; event "break: $vm is down" ;;
    */crash)  ssh_node "$vm" "sudo pkill -9 $(proc_pattern $target); echo killed"
              # systemd Restart=on-failure brings it back in ~10s: record when
              if [ $DRY = 0 ]; then local i; for i in $(seq 1 30); do sleep 3
                if ssh_node "$vm" "systemctl is-active -q $(unit_of $target) && pgrep $(proc_pattern $target) >/dev/null" ; then event "recovered: $target restarted by systemd on $vm (+$((i*3))s)"; break; fi; done; fi ;;
    */dead)   ssh_node "$vm" "sudo systemctl stop $(unit_of $target); echo stopped" ;;
    */hang)   ssh_node "$vm" "sudo pkill -STOP $(proc_pattern $target); echo paused" ;;
  esac
  c_ok "fault injected — watch the probes / run: ./demo.sh status"
}

cmd_restore(){ # reverse every fault in .state/faults, newest first
  need_hosts
  c_hdr "restore: reverse all faults"
  if [ $DRY = 1 ]; then echo "[dry-run] reverse $FAULTS (newest first): vm stop -> start; dead -> systemctl start; hang -> kill -CONT; crash -> verify"; py wait "$HOSTS" 300; return; fi
  [ -s "$FAULTS" ] || { c_warn "no faults recorded"; }
  local FL=(); [ -s "$FAULTS" ] && mapfile -t FL < <(tac "$FAULTS")     # read first: gcloud/ssh inside the loop would eat a piped stdin
  local line ts target mode vm
  for line in "${FL[@]}"; do read -r ts target mode vm <<<"$line"
    [ -n "$vm" ] || continue
    case "$target/$mode" in
      vm/stop)  event "restore: start $vm"; gc compute instances start "$vm" --zone="$(zone_of "$vm")" ;;
      */dead)   event "restore: systemctl start $(unit_of $target) on $vm"; ssh_node "$vm" "sudo systemctl start $(unit_of $target)" ;;
      */hang)   event "restore: resume $target on $vm"; ssh_node "$vm" "sudo pkill -CONT $(proc_pattern $target)" ;;
      */crash)  event "restore: verify $target on $vm"; ssh_node "$vm" "sudo systemctl start $(unit_of $target)" ;;
    esac
  done
  refresh_hosts >/dev/null
  echo "  waiting for the cluster to be healthy…"
  py wait "$HOSTS" 480      # double faults: FEs need time to become catalog-ready and BEs to re-register
  event "restore: cluster healthy"
  py status "$HOSTS"
  rm -f "$FAULTS"
}

cmd_measure(){
  [ $OPT_JSON = 1 ] || c_hdr "measure${OPT_LABEL:+ ($OPT_LABEL)}"
  [ $DRY = 1 ] && { echo "[dry-run] scp $CLIENT_VM:/opt/probe/log/*.log -> $STATE/; cluster.py measure each"; return; }
  for p in "${PROBES[@]}"; do scp_from "$CLIENT_VM" "/opt/probe/log/$p.log" "$STATE/probe-$p.log" || true; done
  if [ -n "$OPT_LABEL" ]; then mkdir -p "$HERE/logs"; for p in "${PROBES[@]}"; do [ -s "$STATE/probe-$p.log" ] && cp "$STATE/probe-$p.log" "$HERE/logs/$(date +%F)-$OPT_LABEL-$p.log"; done; fi
  if [ $OPT_JSON = 1 ]; then "$PY" "$HERE/cluster.py" report "$STATE" "$HOSTS"; return; fi
  for p in "${PROBES[@]}"; do
    [ -s "$STATE/probe-$p.log" ] || { c_warn "no log for $p"; continue; }
    printf '\n\033[1m[%s]\033[0m ' "$p"; py measure "$STATE/probe-$p.log"
  done
  echo; need_hosts; py status "$HOSTS" || true
}
# power state changes target only the instances: the generated inventory (external IPs) is refreshed by a second, full apply
tf_power(){ tf apply -input=false -auto-approve -var vm_status="$1" -target=google_compute_instance.doris -target=google_compute_instance.client; }
cmd_stop(){ c_hdr "stop all VMs (terraform vm_status=TERMINATED)"; probe_stop; tf_power TERMINATED; c_ok "stopped (disks kept)"; }
cmd_start(){ c_hdr "start all VMs (terraform vm_status=RUNNING)"; tf_power RUNNING; tf apply -input=false -auto-approve -var vm_status=RUNNING; refresh_hosts; ensure_venv; py wait "$HOSTS" 300; py seed "$HOSTS" 10000; py status "$HOSTS"; }
probe_stop(){ if probe_running; then ssh_node "$CLIENT_VM" "sudo systemctl stop probe-mysql probe-jdbc probe-flight" || true; rm -f "$PROBES_ON"; echo "  probes stopped on $CLIENT_VM"; fi; }

cmd_down(){
  c_hdr "down: terraform destroy ($NAME_PREFIX-*, $CLIENT_VM, $FW_RULE; APIs and Cloud Run stay)"
  if [ $YES = 0 ] && [ $DRY = 0 ]; then read -r -p "  type 'delete' to confirm: " ans; [ "$ans" = "delete" ] || { echo "  aborted"; exit 1; }; fi
  probe_stop
  tf destroy -input=false -auto-approve
  [ $DRY = 1 ] || rm -f "$HOSTS" "$FAULTS" "$HERE/ansible/inventory.ini"
  c_ok "all resources deleted — only this directory remains"
}

cmd_auto(){
  local t0; t0=$(date +%s)
  cmd_up
  c_hdr "auto: baseline ${AUTO_BASELINE}s of probe"
  MONITOR_BG=1 cmd_monitor
  [ $DRY = 1 ] || sleep "$AUTO_BASELINE"
  cmd_break
  c_hdr "auto: node down for ${AUTO_OUTAGE}s — probe keeps writing"
  [ $DRY = 1 ] || { sleep "$AUTO_OUTAGE"; probe_tail 4; }
  cmd_restore
  [ $DRY = 1 ] || sleep 20
  probe_stop
  cmd_measure
  if [ $KEEP = 1 ]; then c_warn "--keep: leaving VMs running (~\$0.49/hr)"; else YES=1 cmd_down; fi
  c_ok "auto finished in $(( $(date +%s) - t0 ))s"
}

case "$CMD" in
  up) cmd_up;; status) cmd_status;; monitor) cmd_monitor;; break) cmd_break;; restore) cmd_restore;;
  measure) cmd_measure;; stop) cmd_stop;; start) cmd_start;; down) cmd_down;; auto) cmd_auto;; client) ensure_client_vm;; plan) cmd_plan;;
  *) sed -n '2,13p' "$0";;
esac
