#!/usr/bin/env python3
"""Build site/howto.html — 部署與操作：Terraform / Ansible 分工、環境與可用性狀態機、實驗指令。
Run: ./venv/bin/python site/build_howto.py"""
import pathlib, sys, html
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, lvl

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_N = 'font-family="Inter,Noto Sans TC,sans-serif" font-size="12" font-weight="600" fill="#0f1a14"'
FONT_S = 'font-family="JetBrains Mono,monospace" font-size="9" fill="#4f5e56"'
FONT_L = 'font-family="JetBrains Mono,monospace" font-size="8" fill="#4f5e56" letter-spacing="0.06em"'
INK, MUTED, RULE, GREEN, TINT, WHITE = "#0f1a14", "#4f5e56", "#d9eee8", "#11a679", "rgba(17,166,121,.10)", "#fff"

def box(x, y, w, h, name, sub="", focal=False, dashed=False, tag=""):
    fill = TINT if focal else WHITE; stroke = GREEN if focal else (RULE if dashed else INK)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{WHITE}"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{1.2 if focal else 1}"{dash}/>'
    if tag: s += f'<rect x="{x+8}" y="{y+6}" width="{8+len(tag)*6}" height="12" rx="2" fill="transparent" stroke="rgba(15,26,20,.3)" stroke-width="0.8"/><text x="{x+12+len(tag)*3}" y="{y+15}" {FONT_L} text-anchor="middle">{tag}</text>'
    cy = y + h/2 + (2 if not sub else -4)
    s += f'<text x="{x+w/2}" y="{cy+2}" {FONT_N} text-anchor="middle">{html.escape(name)}</text>'
    if sub: s += f'<text x="{x+w/2}" y="{cy+16}" {FONT_S} text-anchor="middle">{html.escape(sub)}</text>'
    return s

def label(x, y, text, color=MUTED):
    w = 8 + len(text) * 5.4
    return f'<rect x="{x-w/2}" y="{y-9}" width="{w}" height="12" rx="2" fill="{WHITE}"/><text x="{x}" y="{y}" {FONT_L} fill="{color}" text-anchor="middle">{html.escape(text)}</text>'

def arrow(d, dashed=False, color=MUTED, marker="arrow"):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.2"{" stroke-dasharray=\"4,3\"" if dashed else ""} marker-end="url(#{marker})"/>'

DEFS = f'<defs><marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker><marker id="arrow-g" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{GREEN}"/></marker></defs>'

# ---------- 1. tooling flow: local -> terraform -> GCP ; ansible -> nodes ; demo.sh -> actions ----------
def flow_svg():
    s = [f'<svg viewBox="0 0 960 400" role="img" aria-labelledby="fl-t fl-d" xmlns="http://www.w3.org/2000/svg"><title id="fl-t">工具分工：Terraform、Ansible、demo.sh</title><desc id="fl-d">本機的 demo.sh 呼叫 Terraform 建立 GCP 資源並產生 inventory，Ansible 依 inventory 設定四台 VM，demo.sh 再透過 gcloud 與 ssh 對叢集做故障注入與量測。</desc>{DEFS}<rect width="100%" height="100%" fill="{WHITE}"/>']
    # zones
    s.append(f'<rect x="40" y="48" width="240" height="312" rx="8" fill="rgba(15,26,20,.02)" stroke="{RULE}"/><rect x="48" y="52" width="88" height="12" rx="2" fill="{WHITE}"/><text x="92" y="61" {FONT_L} text-anchor="middle">本機 (WSL)</text>')
    s.append(f'<rect x="360" y="48" width="560" height="312" rx="8" fill="rgba(15,26,20,.02)" stroke="{RULE}"/><rect x="368" y="52" width="136" height="12" rx="2" fill="{WHITE}"/><text x="436" y="61" {FONT_L} text-anchor="middle">GCP · project doris-poc</text>')
    # arrows first
    s.append(arrow("M240,112 H400", color=GREEN, marker="arrow-g")); s.append(label(320, 104, "TERRAFORM APPLY", GREEN))
    s.append(arrow("M240,216 H400")); s.append(label(320, 208, "ANSIBLE-PLAYBOOK"))
    s.append(arrow("M240,320 H400")); s.append(label(320, 312, "GCLOUD / SSH"))
    s.append(arrow("M160,144 V184", dashed=True)); s.append(label(212, 168, "INVENTORY.INI"))
    s.append(arrow("M480,144 V184", dashed=True)); s.append(label(536, 168, "4 VM READY"))
    s.append(arrow("M480,248 V288", dashed=True)); s.append(label(548, 272, "CLUSTER READY"))
    s.append(arrow("M640,320 H760")); s.append(label(700, 312, "BREAK / RESTORE"))
    # boxes
    s.append(box(80, 80, 160, 64, "Terraform", "infra/  資源存在什麼", focal=True, tag="IaC"))
    s.append(box(80, 184, 160, 64, "Ansible", "ansible/  機器裡長什麼樣", tag="CFG"))
    s.append(box(80, 288, 160, 64, "demo.sh", "monitor · break · measure", tag="OPS"))
    s.append(box(400, 80, 160, 64, "VM ×4 · 防火牆 · API", "vm_status 開關機", tag="GCE"))
    s.append(box(400, 184, 160, 64, "Doris FE+BE ×3", "systemd · conf · 叢集註冊", tag="NODE"))
    s.append(box(400, 288, 240, 64, "client VM · 三個探測", "probe-mysql / jdbc / flight", tag="CLI"))
    s.append(box(760, 288, 128, 64, "故障中的節點", "kill / stop / STOP / VM", dashed=True))
    s.append("</svg>"); return "".join(s)

# ---------- 2. environment state machine ----------
def env_state_svg():
    s = [f'<svg viewBox="0 0 960 336" role="img" aria-labelledby="es-t es-d" xmlns="http://www.w3.org/2000/svg"><title id="es-t">環境狀態機：demo.sh 指令帶來的狀態轉移</title><desc id="es-d">未建立經 up 成為健康；健康經 monitor 成為監控中，經 break 成為故障中，restore 回到健康；stop 與 start 在健康與關機之間切換；down 回到未建立。</desc>{DEFS}<rect width="100%" height="100%" fill="{WHITE}"/>']
    # states: 未建立(60,120) 健康(300,120) 監控中(540,120) 故障中(780,120) 關機(300,248)
    s.append(f'<circle cx="24" cy="152" r="6" fill="{INK}"/>')
    s.append(arrow("M30,152 H60"))
    s.append(arrow("M200,152 H300", color=GREEN, marker="arrow-g")); s.append(label(250, 144, "UP", GREEN))
    s.append(arrow("M440,152 H540")); s.append(label(490, 144, "MONITOR"))
    s.append(arrow("M680,152 H780")); s.append(label(730, 144, "BREAK (可疊加)"))
    # restore: 故障中 -> 健康, routed below
    s.append(arrow("M860,184 V216 Q860,224 852,224 H448 Q440,224 440,216 V184")); s.append(label(650, 216, "RESTORE (逆序逆轉全部故障)"))
    # self loop on 故障中: crash auto recover
    s.append(arrow("M820,120 V96 Q820,88 828,88 H892 Q900,88 900,96 V120")); s.append(label(860, 80, "CRASH → SYSTEMD 拉起"))
    # stop / start between 健康 and 關機
    s.append(arrow("M340,184 V248")); s.append(label(300, 220, "STOP"))
    s.append(arrow("M400,248 V184")); s.append(label(452, 220, "START (自動歸隊)"))
    # down: 關機 -> 未建立 and 健康 -> 未建立 (single annotation)
    s.append(arrow("M300,280 H140 Q132,280 132,272 V184", dashed=True)); s.append(label(216, 272, "DOWN (terraform destroy)"))
    s.append(box(60, 120, 140, 64, "未建立", "沒有任何資源", dashed=True))
    s.append(box(300, 120, 140, 64, "健康", "3 FE · 3 BE · 12 副本 OK", focal=True))
    s.append(box(540, 120, 140, 64, "監控中", "三個探測每秒讀寫"))
    s.append(box(780, 120, 140, 64, "故障中", ".state/faults 記錄"))
    s.append(box(300, 248, 140, 64, "關機", "只剩磁碟費"))
    s.append(f'<text x="60" y="320" {FONT_L}>* 任一狀態都能 STATUS 查看；--dry-run 不改變狀態</text>')
    s.append("</svg>"); return "".join(s)

# ---------- 3. availability state machine (cluster) ----------
def avail_state_svg():
    s = [f'<svg viewBox="0 0 960 352" role="img" aria-labelledby="as-t as-d" xmlns="http://www.w3.org/2000/svg"><title id="as-t">叢集可用性狀態機</title><desc id="as-d">FE 與 BE 各自的存活數決定可用性：兩層都至少 2 個存活時讀寫正常；BE 只剩 1 個時只讀；FE 只剩 1 個時不可用；master FE 被暫停但連線仍在時進入卡住，直到重新選主或恢復。</desc>{DEFS}<rect width="100%" height="100%" fill="{WHITE}"/>']
    # states: 讀寫正常(380,64) center ; 只讀(120,208) ; 不可用(640,208) ; 卡住(380,208)
    s.append(arrow("M380,128 V176 Q380,184 372,184 H288 Q280,184 280,192 V208")); s.append(label(330, 176, "BE 存活 = 1"))
    s.append(arrow("M280,272 V296 Q280,304 288,304 H400 Q408,304 408,296 V128", dashed=True)); s.append(label(344, 296, "BE 回到 ≥ 2"))
    s.append(arrow("M500,128 V176 Q500,184 508,184 H592 Q600,184 600,192 V208")); s.append(label(550, 176, "FE 存活 = 1"))
    s.append(arrow("M600,272 V296 Q600,304 592,304 H480 Q472,304 472,296 V128", dashed=True)); s.append(label(536, 296, "FE 回到 ≥ 2"))
    s.append(arrow("M440,128 V208")); s.append(label(496, 168, "MASTER FE HANG"))
    s.append(arrow("M420,272 V296 Q420,304 428,304 H452 Q460,304 460,296 V128", dashed=True)); s.append(label(504, 320, "63s 後重新選主 或 恢復"))
    s.append(arrow("M280,208 V184 Q280,176 288,176 H352 Q360,176 360,184 V208", dashed=True))
    s.append(box(300, 64, 200, 64, "讀寫正常", "FE ≥ 2 且 BE ≥ 2", focal=True))
    s.append(box(200, 208, 160, 64, "只讀", "寫入失敗、SELECT 正常"))
    s.append(box(360, 208, 160, 64, "卡住", "client 等逾時、無回應"))
    s.append(box(520, 208, 160, 64, "不可用", "連查詢都失敗", dashed=True))
    s.append(f'<text x="60" y="340" {FONT_L}>* 只讀 + FE 再掛一個 → 不可用（兩層都剩 1/3）；等級由 measure 依故障中最後 30 秒的操作判定</text>')
    s.append("</svg>"); return "".join(s)

body = f'''<div class="hero"><div class="container"><p class="eyebrow">部署與操作 · 給同事的說明</p>
<h1 class="display">怎麼<em>部署</em>、狀態怎麼變、<em>指令</em>怎麼下</h1>
<p class="lede">這頁講三件事：<b>Terraform 與 Ansible 各自負責什麼</b>（資源 vs 設定）、<b>環境與叢集的狀態機</b>（哪個指令把系統帶到哪個狀態、叢集在什麼條件下讀寫正常 / 只讀 / 不可用），以及<b>從零到跑完一輪實驗的指令</b>。</p>
<p><a class="btn ghost" href="index.html">← 精簡報告</a> <a class="btn ghost" href="specs.html">實驗設計</a> <a class="btn ghost" href="results.html">結果</a></p></div></div>
<div class="container">

<section id="layers"><h2 class="title"><small>01 · LAYERS</small>三層分工</h2>
<p class="sub">原則：<b>狀態</b>交給宣告式工具（Terraform 管雲端資源、Ansible 管機器內設定），<b>動作</b>留在 shell。這樣 up / down 是 apply / destroy，重跑不會壞；break / restore / measure 這種一次性動作才用腳本。</p>
<figure><div class="figure">{flow_svg()}</div><figcaption>實線＝誰呼叫誰；虛線＝產出物或前置條件。demo.sh up 依序做前兩條實線，之後的實驗只走第三條。</figcaption></figure>
<div class="tablewrap" style="margin-top:18px"><table><thead><tr><th>層</th><th>工具 / 目錄</th><th>負責</th><th>不負責</th><th>對應指令</th></tr></thead><tbody>
<tr><td><b>資源</b></td><td>Terraform · <code>infra/</code></td><td>GCP 上「存在什麼」：4 台 VM（3 Doris + 1 client）、防火牆、API、VM 開關機、產生 Ansible inventory</td><td>機器裡的軟體、叢集成員</td><td><code>demo.sh up / stop / start / down / plan</code></td></tr>
<tr><td><b>設定</b></td><td>Ansible · <code>ansible/</code></td><td>機器裡「長什麼樣」：JDK、Doris、conf、systemd、FE/BE 註冊、client VM 的三個探測</td><td>開關機、故障注入、量測</td><td><code>demo.sh up / client / plan</code></td></tr>
<tr><td><b>動作</b></td><td><code>demo.sh</code> · <code>experiments/</code></td><td>monitor / break / restore / measure；矩陣執行器、結果回填、網站</td><td>描述狀態</td><td><code>demo.sh monitor / break / restore / measure</code>、<code>run_matrix.py</code></td></tr>
</tbody></table></div></section>

<section id="terraform"><h2 class="title"><small>02 · TERRAFORM</small>資源層做什麼</h2>
<div class="grid2"><div>
<ul class="notes">
<li><b>資源：</b><code>google_compute_instance.doris[3]</code>（asia-east1-a/b/c，e2-standard-4，tag <code>doris</code>）、<code>google_compute_instance.client</code>（e2-small）、<code>google_compute_firewall.operator</code>（9030/8030/8040 只放行操作者 IP）、<code>google_project_service</code>（compute / run / cloudbuild / artifactregistry，destroy 不關閉）、選用的 Cloud Run 服務。</li>
<li><b>開關機也是宣告：</b>變數 <code>vm_status = RUNNING | TERMINATED</code> 對應 instance 的 <code>desired_status</code>，<code>demo.sh stop / start</code> 就是換這個變數再 apply（只針對 instance 資源）。</li>
<li><b>inventory 由 Terraform 產生：</b><code>inventory.tftpl</code> 把每台 VM 的名稱、內外網 IP、zone、哪台是 FE seed 寫成 <code>ansible/inventory.ini</code>。開機後外部 IP 會變，所以 start 會再 apply 一次更新它。</li>
<li><b>認證不用 ADC：</b><code>infra/tf.sh</code> 用 <code>gcloud auth print-access-token</code> 當 <code>GOOGLE_OAUTH_ACCESS_TOKEN</code>，並自動帶 <code>allow_ip</code>（目前對外 IP）與 <code>ssh_user</code>。</li>
<li><b>現有資源用 import 接管：</b>第一次導入時把手動建的 VM / 防火牆 / API import 進 state，plan 只有原地更新，沒有重建。</li>
</ul></div>
<pre><code># infra/main.tf（節錄）
resource "google_compute_instance" "doris" {{
  count        = length(var.zones)          # a, b, c
  name         = "${{var.name_prefix}}-${{count.index + 1}}"
  zone         = "${{var.region}}-${{var.zones[count.index]}}"
  machine_type = var.machine_type
  tags         = ["doris"]
  desired_status            = var.vm_status # RUNNING / TERMINATED
  allow_stopping_for_update = true
  lifecycle {{ ignore_changes = [boot_disk[0].initialize_params[0].image] }}
}}

resource "local_file" "inventory" {{
  filename = "../ansible/inventory.ini"
  content  = templatefile("inventory.tftpl", {{ nodes = ..., client = ... }})
}}

# demo.sh 裡的用法
infra/tf.sh apply -var vm_status=RUNNING \\
  -target=google_compute_instance.doris -target=google_compute_instance.client
infra/tf.sh apply -var vm_status=RUNNING     # 第二次：更新 inventory
infra/tf.sh destroy                          # demo.sh down</code></pre></div></section>

<section id="ansible"><h2 class="title"><small>03 · ANSIBLE</small>設定層做什麼</h2>
<div class="grid2"><div>
<p class="sub"><code>ansible/site.yml</code> 三個 play 依序跑，全部可重跑（第二次 <code>changed=0</code>），<code>--check --diff</code> 可預演。</p>
<div class="tablewrap"><table><thead><tr><th>Play / role</th><th>對象</th><th>做什麼</th></tr></thead><tbody>
<tr><td><b>doris_node</b></td><td>doris ×3</td><td>apt（JDK 17、mysql client）→ sysctl / limits / THP → 下載解壓 Doris 4.1.1（已存在則跳過）→ <code>blockinfile</code> 寫 fe.conf / be.conf（priority_networks、資料目錄、heap、mem_limit）→ <code>fe.env</code>（follower 帶 <code>--helper seed:9010</code>）→ systemd unit <code>doris-fe</code> / <code>doris-be</code>（enable；handler 只在已運行時 restart）</td></tr>
<tr><td><b>doris_cluster</b></td><td>doris（動作在 seed）</td><td>起 seed FE、等 9030；舊叢集沒 quorum 就先起全部 FE → <code>ALTER SYSTEM ADD FOLLOWER / BACKEND</code>（已存在忽略）→ 全部 FE / BE start</td></tr>
<tr><td><b>probe_client</b></td><td>client ×1</td><td>時區、JDK、venv（pymysql / pyarrow / adbc）、Connector/J、javac → 三個 unit <code>probe-mysql / jdbc / flight</code>（不 enable，由 monitor 啟動；程式碼變更時自動 restart）</td></tr>
</tbody></table></div>
<ul class="notes" style="margin-top:14px">
<li><b>變數集中在</b> <code>group_vars/all.yml</code>：Doris 版本與下載網址、路徑、priority_networks、FE heap、BE mem_limit、探測指令。</li>
<li><b>inventory 不手寫</b>，來自 Terraform；<code>fe_seed=true</code> 那台負責註冊其他節點。</li>
<li><b>sh 對照：</b>原本的 <code>grep -q || cat >></code> 變成 <code>blockinfile</code>、<code>ln -sfn</code> 變成 <code>file state=link</code>、<code>curl + tar</code> 變成 <code>get_url + unarchive creates=</code>、<code>nohup</code> 變成 systemd + handler。</li>
</ul></div>
<pre><code># ansible/roles/doris_node/tasks/main.yml（節錄）
- name: FE conf block
  ansible.builtin.blockinfile:
    path: "{{{{ doris_home }}}}/fe/conf/fe.conf"
    marker: "# {{mark}} ANSIBLE doris-poc"
    block: |
      priority_networks = {{{{ priority_networks }}}}
      meta_dir = {{{{ doris_base }}}}/data/fe
      JAVA_HOME={{{{ java_home }}}}
  notify: restart doris-fe

- name: systemd units
  ansible.builtin.template:
    src: "{{{{ item }}}}.service.j2"
    dest: "/etc/systemd/system/{{{{ item }}}}.service"
  loop: [doris-fe, doris-be]
  notify: daemon reload

# 執行
./venv/bin/ansible-playbook ansible/site.yml            # 全部
./venv/bin/ansible-playbook ansible/site.yml --check --diff
./venv/bin/ansible-playbook ansible/site.yml --limit client</code></pre></div></section>

<section id="states"><h2 class="title"><small>04 · STATE MACHINES</small>狀態機</h2>
<p class="sub">兩個層次：<b>環境</b>（demo.sh 指令把整個環境帶到哪個狀態）與<b>叢集可用性</b>（FE / BE 存活數決定 client 還能做什麼）。</p>
<figure><div class="figure">{env_state_svg()}</div><figcaption>環境狀態機。故障可以疊加（連續 break），restore 依相反順序全部逆轉；crash 類故障由 systemd 自動拉起，restore 只做健康確認。狀態存在 <code>.state/faults</code>，<code>demo.sh status</code> 隨時可看。</figcaption></figure>
<figure style="margin-top:18px"><div class="figure">{avail_state_svg()}</div><figcaption>叢集可用性狀態機（實驗結果驗證）。FE 三個 FOLLOWER 需 2 個才能選 master 與改 metadata；BE 三副本寫入需 2 份成功。三輪實測：FE 剩 1 → 不可用（連查詢都拿不到 metadata）；BE 剩 1 → 只讀；master FE 被 SIGSTOP → 卡住，第 1 輪 2 分鐘未選主、第 2/3 輪 63 秒後選主。</figcaption></figure>
<div class="tablewrap" style="margin-top:18px"><table><thead><tr><th>叢集狀態</th><th>條件</th><th>client 看到什麼</th><th>measure 判定</th></tr></thead><tbody>
<tr><td>{lvl("rw")}</td><td>FE 存活 ≥ 2 且 BE 存活 ≥ 2</td><td>短暫失敗後全部恢復，中斷多在 0～40 秒</td><td>故障中最後 30 秒有寫入成功</td></tr>
<tr><td>{lvl("ro")}</td><td>BE 存活 = 1（FE ≥ 2）</td><td>INSERT/UPSERT/DELETE 持續失敗，SELECT 正常</td><td>寫入全失敗、讀取檢查成功</td></tr>
<tr><td>{lvl("down")}</td><td>FE 存活 = 1</td><td>僅存 FE 拒絕連線（follower）或全部逾時（master）</td><td>寫入與讀取檢查都失敗</td></tr>
<tr><td>{lvl("stalled")}</td><td>master FE 程序暫停但 TCP 仍在</td><td>jdbc 一筆卡住到恢復、mysql 每筆 8 秒逾時、flight 每筆 9 秒</td><td>最後 30 秒沒有任何操作完成</td></tr>
</tbody></table></div></section>

<section id="commands"><h2 class="title"><small>05 · COMMANDS</small>從零到跑完一輪實驗</h2>
<div class="grid2"><div>
<h3>A. 第一次建環境（約 10 分鐘）</h3>
<pre><code># 前置：gcloud 已登入、terraform ≥ 1.6、python3
./demo.sh plan            # 看 terraform plan + ansible --check --diff
./demo.sh up              # terraform apply → ansible → 灌 1 萬筆
./demo.sh status          # FE 3/3 (master doris-x) BE 3/3 replicas OK</code></pre>
<h3>B. 手動示範一格（demo 時用）</h3>
<pre><code>./demo.sh monitor         # 終端 1：三個 client 即時捲動
./demo.sh break --target fe --mode hang --on master   # 終端 2
./demo.sh status          # FE 存活數、目前故障
./demo.sh restore         # 逆轉全部故障、等健康
./demo.sh measure         # 失敗視窗、卡頓、可用性等級</code></pre>
<h3>C. 跑整個矩陣（每輪約 70 分鐘）</h3>
<pre><code>./venv/bin/python experiments/run_matrix.py --pass 1   # 開機→16 格→關機
./venv/bin/python experiments/run_matrix.py --pass 2
./venv/bin/python experiments/run_matrix.py --pass 3
./experiments/finalize.sh  # 回填 spec → 產三頁 → openspec validate → 部署</code></pre>
<h3>D. 收尾</h3>
<pre><code>./demo.sh stop            # 關機，只剩磁碟費
./demo.sh down            # terraform destroy（要打 delete 確認）</code></pre>
</div><div>
<h3>break 的三個維度</h3>
<div class="tablewrap"><table><thead><tr><th>參數</th><th>值</th><th>意思</th></tr></thead><tbody>
<tr><td><code>--target</code></td><td>fe / be / vm</td><td>對象：FE 程序、BE 程序、整台 VM</td></tr>
<tr><td><code>--mode</code></td><td>crash / dead / hang / stop</td><td>kill -9（systemd 10 秒拉起）／systemctl stop（等人）／kill -STOP（活著不回應）／VM 停機</td></tr>
<tr><td><code>--on</code></td><td>master / follower / &lt;vm&gt;</td><td>位置：用 SHOW FRONTENDS 找 master；BE 的 master 指「master FE 所在那台的 BE」</td></tr>
</tbody></table></div>
<h3 style="margin-top:22px">每格執行器做的事</h3>
<ol class="notes">
<li><code>monitor --fresh</code>：清 log、重啟三個探測（可指定 client 主機順序）</li><li>baseline 30 秒</li><li><code>break …</code>（雙重故障間隔 30 秒）</li><li>觀察 90 秒（hang 類 120 秒）</li><li><code>measure --json</code>（故障中）</li><li><code>restore</code>，等健康（最長 8 分鐘）</li><li>settle 25 秒 → <code>measure --json</code>（恢復後）→ 存 <code>results/pass-N/&lt;id&gt;/</code></li>
</ol>
<h3 style="margin-top:22px">量測定義</h3>
<ul class="notes">
<li><b>失敗視窗</b>：第一次 FAIL 到下一次 OK</li><li><b>卡頓</b>：連續兩次操作間隔 &gt; 5 秒（例如卡在轉發給已死 master）</li><li><b>受影響秒數</b>：兩者聯集，裁到故障期間</li><li><b>等級</b>：故障中最後 30 秒；寫入失敗後另開連線做讀取檢查以分辨只讀與不可用</li>
</ul>
</div></div></section>

<section id="files"><h2 class="title"><small>06 · FILES</small>檔案地圖</h2>
<div class="tablewrap"><table><thead><tr><th>路徑</th><th>內容</th></tr></thead><tbody>
<tr><td><code>infra/</code></td><td>Terraform：main.tf、variables.tf、outputs.tf、inventory.tftpl、tf.sh</td></tr>
<tr><td><code>ansible/</code></td><td>site.yml、group_vars/all.yml、roles/doris_node · doris_cluster · probe_client；inventory.ini 由 Terraform 產生</td></tr>
<tr><td><code>demo.sh</code>、<code>cluster.py</code></td><td>動作指令；本機端狀態查詢、量測與 log 分析（analyze / report）</td></tr>
<tr><td><code>clients/</code></td><td>probe_common.py、probe_mysql.py、probe_flight.py、Probe.java（部署到 client VM）</td></tr>
<tr><td><code>experiments/</code></td><td>scenarios.yaml（16 格）、run_matrix.py、fill_results.py、finalize.sh</td></tr>
<tr><td><code>openspec/</code></td><td>主 spec（topology / clients / operations）與 change fault-matrix（proposal / design / tasks / delta spec，含實測）</td></tr>
<tr><td><code>results/</code>、<code>site/</code>、<code>deploy/</code></td><td>三輪原始結果與彙整；三頁網站產生器與輸出；Cloud Run 靜態站（nginx）</td></tr>
</tbody></table></div></section>
</div>'''
out = ROOT / "site/howto.html"
out.write_text(shell("Doris HA 部署與操作", "Terraform 與 Ansible 的分工、環境與叢集可用性狀態機、從零到跑完一輪故障矩陣的指令。", body, "howto"), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
