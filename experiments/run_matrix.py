#!/usr/bin/env python3
"""Fault-matrix runner. One pass = start all VMs -> every scenario in scenarios.yaml -> stop all VMs.
Per scenario: monitor -> baseline -> break steps -> observe -> measure (during) -> restore -> settle -> measure (after).
Results: results/pass-N/<id>/{during.json,after.json,summary.json,mysql.log,jdbc.log,flight.log}, plus run.log.

  ./venv/bin/python experiments/run_matrix.py --pass 1                # full pass
  ./venv/bin/python experiments/run_matrix.py --pass 0 --only vm-stop-3clients --no-stop   # smoke test
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, time, datetime
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = str(ROOT / "demo.sh")
STATE = ROOT / ".state"

ap = argparse.ArgumentParser()
ap.add_argument("--pass", dest="pass_no", type=int, required=True)
ap.add_argument("--only", default="", help="comma-separated scenario ids")
ap.add_argument("--no-start", action="store_true"); ap.add_argument("--no-stop", action="store_true")
ap.add_argument("--observe-scale", type=float, default=1.0, help="multiply all wait times (e.g. 0.5 for a quick smoke test)")
args = ap.parse_args()

cfg = yaml.safe_load((ROOT / "experiments" / "scenarios.yaml").read_text(encoding="utf-8"))
D = cfg["defaults"]; scenarios = cfg["scenarios"]
if args.only: scenarios = [s for s in scenarios if s["id"] in args.only.split(",")]
OUT = ROOT / "results" / f"pass-{args.pass_no}"; OUT.mkdir(parents=True, exist_ok=True)
RUNLOG = open(OUT / "run.log", "a", encoding="utf-8")

def now(): return datetime.datetime.now().strftime("%H:%M:%S")
def log(msg):
    line = f"{now()} {msg}"; print(line, flush=True); RUNLOG.write(line + "\n"); RUNLOG.flush()
def wait(sec, why):
    sec = int(sec * args.observe_scale); log(f"  wait {sec}s ({why})"); time.sleep(sec)

def sh(cmd, timeout=600, env=None, quiet=False):
    """Run a demo.sh command, log its output, return (rc, stdout)."""
    e = dict(os.environ); e.update(env or {})
    log(f"$ {' '.join(cmd)}")
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=e, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as ex:
        dec = lambda b: b.decode(errors="replace") if isinstance(b, bytes) else (b or "")
        out = dec(ex.stdout) + dec(ex.stderr) + f"\n[TIMEOUT after {timeout}s]"; p = None
    clean = "\n".join(l for l in out.replace("\x1b[1;36m", "").replace("\x1b[0m", "").splitlines() if l.strip() and not l.strip().startswith("."))
    if not quiet:
        for l in clean.splitlines()[-25:]: RUNLOG.write("    | " + l + "\n")
        RUNLOG.flush()
    return (p.returncode if p else 124), out

def measure_json():
    rc, out = sh([DEMO, "measure", "--json"], timeout=300, quiet=True)
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception as ex:
        log(f"  measure --json unparsable: {ex}"); return {"error": out[-500:]}

def ensure_healthy(label):
    rc, out = sh([str(ROOT / "venv/bin/python"), str(ROOT / "cluster.py"), "wait", str(STATE / "hosts.tsv"), "300"], timeout=360)
    ok = rc == 0; log(f"  cluster {'healthy' if ok else 'NOT healthy'} ({label})")
    return ok

def run_scenario(sc):
    sid = sc["id"]; d = OUT / sid; d.mkdir(exist_ok=True)
    log(f"=== [{sid}] {sc['scenario']}  steps={sc['steps']}")
    t_start = now()
    order = ["--order", sc["order"]] if sc.get("order") else []
    sh([DEMO, "monitor", "--fresh"] + order, env={"MONITOR_BG": "1"}, timeout=300)
    wait(sc.get("baseline", D["baseline"]), "baseline")
    break_times = []
    for k, step in enumerate(sc["steps"]):
        rc, out = sh([DEMO, "break"] + step.split(), timeout=420)
        break_times.append({"step": step, "at": now(), "rc": rc})
        if k < len(sc["steps"]) - 1: wait(sc.get("gap", D["gap"]), "gap between breaks")
    wait(sc.get("observe", D["observe"]), "observe")
    during = measure_json(); (d / "during.json").write_text(json.dumps(during, ensure_ascii=False, indent=1), encoding="utf-8")
    log("  during: " + ", ".join(f"{c}={during[c].get('level_zh')} ({during[c].get('total_impact_secs')}s)" for c in ("mysql", "jdbc", "flight") if c in during) + f"  alive={during.get('alive')}")
    t_restore = now()
    rc, out = sh([DEMO, "restore"], timeout=900)
    healthy = rc == 0 or ensure_healthy("after restore")
    if not healthy:
        log("  restore did not converge — second attempt"); sh([DEMO, "restore"], timeout=900); healthy = ensure_healthy("after 2nd restore")
    wait(sc.get("settle", D["settle"]), "settle")
    after = measure_json(); (d / "after.json").write_text(json.dumps(after, ensure_ascii=False, indent=1), encoding="utf-8")
    for p in ("mysql", "jdbc", "flight"):
        src = STATE / f"probe-{p}.log"
        if src.exists(): shutil.copy(src, d / f"{p}.log")
    summary = {"id": sid, "scenario": sc["scenario"], "also": sc.get("also", []), "pass": args.pass_no, "order": sc.get("order"),
               "steps": sc["steps"], "started": t_start, "restore_at": t_restore, "ended": now(), "healthy_after": healthy,
               "breaks": break_times,
               "during": {c: {k: during[c].get(k) for k in ("level", "level_zh", "total_impact_secs", "windows", "failed", "failed_by_type", "reconnects", "window_ops", "read_only_client")} for c in ("mysql", "jdbc", "flight") if c in during},
               "after": {c: {k: after[c].get(k) for k in ("level", "level_zh", "total_impact_secs", "windows", "failed", "failed_by_type", "reconnects", "events")} for c in ("mysql", "jdbc", "flight") if c in after},
               "alive_during": during.get("alive"), "alive_after": after.get("alive")}
    (d / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"  after:  " + ", ".join(f"{c}={after[c].get('level_zh')} fails={after[c].get('failed')} impact={after[c].get('total_impact_secs')}s" for c in ("mysql", "jdbc", "flight") if c in after) + f"  alive={after.get('alive')}  healthy={healthy}")
    return summary

log(f"##### pass {args.pass_no} start: {len(scenarios)} scenario(s) {[s['id'] for s in scenarios]}")
if not args.no_start:
    sh([DEMO, "start"], timeout=900)
if not ensure_healthy("before pass"):
    log("cluster not healthy at start — trying restore + ansible client-less recovery"); sh([DEMO, "restore"], timeout=900)
    if not ensure_healthy("after recovery"): log("ABORT: cluster unhealthy"); sys.exit(1)
results = []
for sc in scenarios:
    try:
        results.append(run_scenario(sc))
    except Exception as ex:
        log(f"  !! scenario {sc['id']} raised {type(ex).__name__}: {ex}")
        sh([DEMO, "restore"], timeout=900); ensure_healthy("after exception")
(OUT / "pass-summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
sh([DEMO, "measure"], timeout=300, quiet=True)   # leave last logs in .state for inspection
if not args.no_stop:
    sh([DEMO, "stop"], timeout=900)
log(f"##### pass {args.pass_no} done: {len(results)}/{len(scenarios)} scenarios")
