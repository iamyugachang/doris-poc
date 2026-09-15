#!/usr/bin/env python3
"""Render the experiment design page site/specs.html from openspec/ (design + hypotheses only, no measured results):
architecture diagrams, method, expected matrix, scenario tables; the raw OpenSpec documents sit in a collapsed appendix.
Run: ./venv/bin/python site/build_specs.py"""
import re, html, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, steps, lvl
from svgkit import FONT_L, RULE, GREEN, WHITE, box, label, arrow, DEFS
import markdown, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OS = ROOT / "openspec"
CH = next(d for d in [OS / "changes" / "fault-matrix", *sorted((OS / "changes" / "archive").glob("*-fault-matrix"), reverse=True)] if d.is_dir())   # active or archived change
OUT = ROOT / "site" / "specs.html"
MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
def md(text): MD.reset(); return MD.convert(text)
def inline(t): return MD.convert(t).replace("<p>", "").replace("</p>", "")
def slug(s): return re.sub(r"[^a-z0-9一-鿿]+", "-", s.lower()).strip("-")

# ---------- diagrams ----------
def experiment_svg():
    """Experiment setup: client VM (3 probes + logs) → Doris ×3; demo.sh break injects, measure reads the logs."""
    s = [f'<svg viewBox="0 0 960 392" role="img" aria-labelledby="ex-t ex-d" xmlns="http://www.w3.org/2000/svg"><title id="ex-t">實驗架構：探測、注入、量測</title><desc id="ex-d">client VM 上三個探測程式以多主機清單連三台 Doris VM 並每秒寫一行 log；demo.sh break 對任一台的 FE、BE 或整台 VM 注入故障並在 log 記 EVENT；demo.sh measure 讀 log 算出可用性等級與中斷秒數。</desc>{DEFS}<rect width="100%" height="100%" fill="{WHITE}"/>']
    s.append(f'<rect x="40" y="48" width="280" height="232" rx="8" fill="rgba(15,26,20,.02)" stroke="{RULE}"/><rect x="48" y="52" width="152" height="12" rx="2" fill="{WHITE}"/><text x="124" y="61" {FONT_L} text-anchor="middle">doris-client · 同一 VPC</text>')
    s.append(f'<rect x="400" y="48" width="520" height="232" rx="8" fill="rgba(15,26,20,.02)" stroke="{RULE}"/><rect x="408" y="52" width="176" height="12" rx="2" fill="{WHITE}"/><text x="496" y="61" {FONT_L} text-anchor="middle">Doris ×3 · asia-east1 a / b / c</text>')
    # arrows first
    s.append(arrow("M296,128 H424")); s.append(label(360, 116, "多主機清單 9030 / 8070"))
    s.append(arrow("M180,160 V200")); s.append(label(240, 184, "每秒一行 OK / FAIL"))
    s.append(arrow("M180,256 V304")); s.append(label(232, 284, "measure 讀 log"))
    s.append(arrow("M424,336 H368 Q360,336 360,328 V236 Q360,228 352,228 H296", dashed=True)); s.append(label(404, 280, "EVENT 行"))
    s.append(arrow("M536,304 V168", color=GREEN, marker="arrow-g")); s.append(label(620, 240, "對 FE / BE / VM 注入", GREEN))
    # boxes
    s.append(box(64, 96, 232, 64, "探測 ×3", "mysql / jdbc / arrow-flight · 每秒一步", tag="PROBE"))
    s.append(box(64, 200, 232, 56, "client log ×3", "OK · FAIL · EVENT", dashed=True, tag="LOG"))
    s.append(box(64, 304, 232, 64, "demo.sh measure", "可用性等級 + 中斷秒數", tag="MEASURE"))
    for i, z in enumerate("abc"):
        s.append(box(424 + i * 168, 96, 144, 72, f"doris-{i+1}", "FE + BE", tag=f"ZONE {z.upper()}"))
    s.append(box(424, 304, 224, 64, "demo.sh break", "crash · dead · hang · stop", focal=True, tag="INJECT"))
    s.append("</svg>"); return "".join(s)

def cell_flow_svg(n_cells):
    """One matrix cell from monitor to the final measure; repeated three passes."""
    steps_ = [("monitor", "三個 client 開始探測"), ("baseline", "健康期 30 秒"), ("break", "注入 1～3 個故障"), ("觀察", "90～120 秒"),
              ("measure", "等級 + 中斷秒數"), ("restore", "逆序逆轉全部"), ("settle", "等叢集健康"), ("measure", "確認回到讀寫正常")]
    s = [f'<svg viewBox="0 0 960 176" role="img" aria-labelledby="cf-t cf-d" xmlns="http://www.w3.org/2000/svg"><title id="cf-t">每格實驗的流程</title><desc id="cf-d">每一格依序執行 monitor、30 秒基準、break、觀察、measure、restore、等待健康、再 measure；整個矩陣跑三輪，每輪從全部 VM 開機開始。</desc>{DEFS}<rect width="100%" height="100%" fill="{WHITE}"/>']
    for i in range(len(steps_) - 1):
        x = 16 + i * 120; s.append(arrow(f"M{x+96},76 H{x+120}"))
    for i, (name, sub) in enumerate(steps_):
        s.append(box(16 + i * 120, 48, 96, 56, name, sub, focal=(name == "break")))
    s.append(f'<text x="16" y="140" {FONT_L}>每格 3～5 分鐘 · 整個矩陣 {n_cells} 格 · 跑 3 輪，每輪：全部 VM 開機 → 逐格跑完 → 全部關機 · 結果寫 results/pass-N/&lt;id&gt;/</text>')
    s.append("</svg>"); return "".join(s)

# ---------- parsing openspec ----------
LEVELS = [("讀寫正常", "rw"), ("只讀", "ro"), ("不可用", "down")]
def cell(text):
    """'只讀 或 不可用' / '讀寫正常，短暫中斷' / '—' → level pills + remaining note."""
    t = text.strip()
    if t in ("", "—", "-"): return '<span class="muted">—</span>'
    found = sorted(((t.find(z), z, k) for z, k in LEVELS if z in t))
    rest = t
    for _, z, _ in found: rest = rest.replace(z, "")
    rest = re.sub(r"^[\s，、或/／]+|[\s，、]+$", "", rest.replace("或", "").strip())
    pills = " ".join(lvl(k, z) for _, z, k in found)
    return pills + (f' <span class="note">{html.escape(rest)}</span>' if rest else "")

def parse_design(text):
    """→ (matrix header, matrix rows, open questions) from design.md"""
    sec = {}; cur = None
    for line in text.splitlines():
        m = re.match(r"^## (.+)$", line)
        if m: cur = m.group(1); sec[cur] = []; continue
        if cur: sec[cur].append(line)
    mkey = next(k for k in sec if k.startswith("預期矩陣")); qkey = next(k for k in sec if k.startswith("Open Questions"))
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in sec[mkey] if l.startswith("|") and not re.match(r"^\|\s*-", l)]
    qs = [l[2:].strip() for l in sec[qkey] if l.startswith("- ")]
    return rows[0], rows[1:], qs

def parse_scenarios(text):
    """delta spec → [{name, desc, scenarios:[{name, when, then, level}]}]"""
    reqs = []; req = None; scen = None
    for line in text.splitlines():
        m = re.match(r"^### Requirement:\s*(.+)$", line)
        if m: req = {"name": m.group(1).strip(), "desc": [], "scenarios": []}; reqs.append(req); scen = None; continue
        m = re.match(r"^#### Scenario:\s*(.+)$", line)
        if m: scen = {"name": m.group(1).strip(), "when": "", "then": "", "level": ""}; req["scenarios"].append(scen); continue
        if req is None or line.startswith("## "): continue
        s = line.strip()
        if scen is None:
            if s: req["desc"].append(s)
        elif s.startswith("- **WHEN**"): scen["when"] = s[len("- **WHEN**"):].strip()
        elif s.startswith("- **THEN**"):
            t = s[len("- **THEN**"):].strip()
            if "等級：" in t: t, scen["level"] = [x.strip("；; ") for x in t.rsplit("等級：", 1)]
            scen["then"] = t
    return reqs

def render_spec_body(text):
    """Main-spec renderer (Requirement / Scenario blocks) for the appendix."""
    out = []; req = None; scen = None; buf = []
    def flush_buf(target):
        nonlocal buf
        if buf: target.append(md("\n".join(buf))); buf = []
    def flush_scen():
        nonlocal scen
        if scen: out.append(render_scenario(scen)); scen = None
    def flush_req():
        nonlocal req
        flush_scen()
        if req: out.append("</div></section>"); req = None
    for line in text.splitlines():
        m = re.match(r"^### Requirement:\s*(.+)$", line)
        if m:
            flush_buf(scen["lines"] if scen else out); flush_req(); req = m.group(1).strip()
            out.append(f'<section class="req" id="req-{slug(req)}"><h4><span class="badge">Requirement</span>{html.escape(req)}</h4><div class="req-body">'); continue
        m = re.match(r"^#### Scenario:\s*(.+)$", line)
        if m:
            flush_buf(scen["lines"] if scen else out); flush_scen(); scen = {"name": m.group(1).strip(), "lines": []}; continue
        m = re.match(r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements", line)
        if m:
            flush_buf(scen["lines"] if scen else out); flush_req()
            out.append(f'<p class="delta delta-{m.group(1).lower()}">{m.group(1)} Requirements</p>'); continue
        if re.match(r"^## (Purpose|Requirements)\s*$", line):
            flush_buf(scen["lines"] if scen else out); flush_req(); continue
        if re.match(r"^# ", line): continue
        (scen["lines"] if scen is not None else buf).append(line)
    flush_buf(scen["lines"] if scen else out); flush_req()
    return "".join(out)

def render_scenario(scen):
    when, then, cur = [], [], None
    for l in scen["lines"]:
        s = l.strip()
        if s.startswith("- **WHEN**"): cur = when; when.append(s[len("- **WHEN**"):].strip())
        elif s.startswith("- **THEN**"): cur = then; then.append(s[len("- **THEN**"):].strip())
        elif s.startswith("- ") and cur is not None: cur.append(s[2:].strip())
        elif s and cur is not None: cur.append(s)
    h = [f'<div class="scen"><div class="scen-name">{html.escape(scen["name"])}</div>']
    if when: h.append(f'<div class="wt"><span class="kw">WHEN</span><div>{"<br>".join(inline(w) for w in when)}</div></div>')
    if then: h.append(f'<div class="wt"><span class="kw then">THEN</span><div>{"<br>".join(inline(t) for t in then)}</div></div>')
    h.append("</div>"); return "".join(h)

def render_tasks(text):
    total = len(re.findall(r"^- \[[ xX]\]", text, re.M)); done = len(re.findall(r"^- \[[xX]\]", text, re.M))
    body = re.sub(r"^- \[ \] (\S+) ", r'- <span class="cb"></span><span class="tid">\1</span> ', text, flags=re.M)
    body = re.sub(r"^- \[[xX]\] (\S+) ", r'- <span class="cb on"></span><span class="tid">\1</span> ', body, flags=re.M)
    pct = int(done * 100 / total) if total else 0
    return f'<div class="progress"><div class="bar" style="width:{pct}%"></div></div><p class="muted">{done} / {total} 完成（{pct}%）</p>' + md(body)

# ---------- load ----------
design = (CH / "design.md").read_text(encoding="utf-8"); proposal = (CH / "proposal.md").read_text(encoding="utf-8"); tasks = (CH / "tasks.md").read_text(encoding="utf-8")
fault_spec = (CH / "specs/fault-scenarios/spec.md").read_text(encoding="utf-8"); ops_delta = (CH / "specs/operations/spec.md").read_text(encoding="utf-8")
main_specs = [(d.name, (d / "spec.md").read_text(encoding="utf-8")) for d in sorted((OS / "specs").iterdir()) if (d / "spec.md").exists()]
n_cells = len(yaml.safe_load((ROOT / "experiments/scenarios.yaml").read_text(encoding="utf-8"))["scenarios"])
head, rows, questions = parse_design(design)
reqs = parse_scenarios(fault_spec)
n_sc = sum(len(r["scenarios"]) for r in reqs)
arch_svg = (ROOT / "site/diagrams/arch-normal.svg").read_text(encoding="utf-8")
ex_svg = experiment_svg(); cf_svg = cell_flow_svg(n_cells)
(ROOT / "site/diagrams/experiment.svg").write_text(ex_svg, encoding="utf-8"); (ROOT / "site/diagrams/cell-flow.svg").write_text(cf_svg, encoding="utf-8")
TITLES = {"topology": "拓撲 topology", "clients": "探測 client clients", "operations": "操作契約 operations", "fault-scenarios": "故障情境 fault-scenarios"}

# ---------- sections ----------
matrix = '<div class="tablewrap"><table class="hyp"><thead><tr>' + "".join(f"<th>{html.escape(h)}</th>" for h in head) + "</tr></thead><tbody>"
for r in rows: matrix += f"<tr><td><b>{html.escape(r[0])}</b></td>" + "".join(f"<td>{cell(c)}</td>" for c in r[1:]) + "</tr>"
matrix += "</tbody></table></div>"

scen_html = []
for r in reqs:
    scen_html.append(f'<h3 id="req-{slug(r["name"])}">{html.escape(r["name"])}</h3><p class="sub">{inline(" ".join(r["desc"]))}</p>')
    scen_html.append('<div class="tablewrap"><table class="scen-table"><thead><tr><th>情境</th><th>注入（WHEN）</th><th>預期（THEN）</th><th>等級</th></tr></thead><tbody>')
    for sc in r["scenarios"]:
        scen_html.append(f'<tr><td><b>{html.escape(sc["name"])}</b></td><td>{inline(sc["when"])}</td><td>{inline(sc["then"])}</td><td>{cell(sc["level"]) if sc["level"] else "<span class=muted>—</span>"}</td></tr>')
    scen_html.append("</tbody></table></div>")

appendix = [f'<details><summary>Proposal（為什麼、改什麼）</summary><div class="doc">{md(proposal)}</div></details>',
            f'<details><summary>Design（決策、風險）</summary><div class="doc">{md(design)}</div></details>',
            f'<details><summary>Delta spec · operations（break / restore / measure 的新契約）</summary><div class="doc">{render_spec_body(ops_delta)}</div></details>']
for n, t in main_specs:
    appendix.append(f'<details><summary>主 spec · {TITLES.get(n, n)}</summary><div class="doc">{render_spec_body(t)}</div></details>')
appendix.append(f'<details><summary>Tasks</summary><div class="doc">{render_tasks(tasks)}</div></details>')

nav = ['<div class="lbl">目錄</div>', '<a href="#arch">01 架構</a>', '<a href="#method">02 方法</a>', '<a href="#hyp">03 假設</a>', '<a href="#scen">04 情境</a>']
nav += [f'<a href="#req-{slug(r["name"])}" class="sub-link">· {html.escape(r["name"])}</a>' for r in reqs]
nav += ['<a href="#appendix">附錄 · OpenSpec 原文</a>', '<div class="lbl">看結果</div>', '<a href="results.html">03 過程與結果 →</a>']

body = f'''<div class="hero"><div class="container">{steps("specs")}<p class="eyebrow">Step 02 · 實驗設計（OpenSpec）</p>
<h1 class="display">先講清楚<em>要驗證什麼</em>，再動手</h1>
<p class="lede">三台 VM 各跑一個 FE 與一個 BE。我們對 <b>FE、BE、整台 VM</b> 各用 <b>crash / dead / hang / stop</b> 注入故障，共 {n_cells} 格，每格跑三輪，看 client 是「讀寫正常」、「只讀」還是「不可用」。這頁只有設計與假設，數字在下一頁。</p>
<p><a class="btn" href="results.html">看實驗過程與結果 →</a> <a class="btn ghost" href="index.html">← 精簡報告</a></p></div></div>
<div class="container"><div class="layout"><nav class="side">{"".join(nav)}</nav><main>

<section id="arch"><h2 class="title"><small>01 · ARCHITECTURE</small>架構</h2>
<p class="sub">受測系統與實驗工具各一張圖。</p>
<figure><div class="figure">{arch_svg}</div><figcaption>受測系統：3 台 VM（asia-east1 a / b / c）各 1 FE + 1 BE。FE 三個 FOLLOWER 以多數決選 1 個 master；資料三副本，每個 zone 一份。client 以多主機清單連 FE，不經 Load Balancer。</figcaption></figure>
<figure style="margin-top:18px"><div class="figure">{ex_svg}</div><figcaption>實驗工具：三個探測（mysql / jdbc / arrow-flight）每秒對同一把 key 做 INSERT → UPSERT → SELECT → DELETE → SELECT 並寫 log；<b>break</b> 對任一台的 FE、BE 或整台 VM 注入故障並在 log 記 EVENT；<b>measure</b> 讀 log 算等級與中斷秒數；restore 逆序把故障全部還原。</figcaption></figure>
</section>

<section id="method"><h2 class="title"><small>02 · METHOD</small>方法</h2>
<figure><div class="figure">{cf_svg}</div><figcaption>每一格的流程。break 之後觀察 90 秒（hang 類 120 秒）再量；restore 之後再量一次確認回到讀寫正常。</figcaption></figure>
<div class="cards method" style="margin-top:18px">
<div class="card"><div class="k">注入方式</div><table class="mini"><tbody>
<tr><td><b>crash</b></td><td><code>kill -9</code>，systemd 10 秒後拉起</td></tr>
<tr><td><b>dead</b></td><td><code>systemctl stop</code>，不自動起，等 restore</td></tr>
<tr><td><b>hang</b></td><td><code>kill -STOP</code>，程序在、埠在、不回應</td></tr>
<tr><td><b>stop</b></td><td>整台 VM <code>gcloud compute instances stop</code></td></tr>
</tbody></table></div>
<div class="card"><div class="k">對象 × 位置</div><p>對象：<b>FE</b> / <b>BE</b> / <b>VM</b>。位置：<b>master 所在</b> / <b>follower 所在</b>（由 <code>SHOW FRONTENDS</code> 即時解析）。雙重故障 = 連續兩次 break 疊加，restore 逆序全部還原。</p></div>
<div class="card"><div class="k">量什麼</div><p><b>可用性等級</b>：故障中最後 30 秒的操作成功率 → 讀寫正常 / 只讀 / 不可用（arrow-flight 只判讀取）。<b>中斷秒數</b>：第一次 FAIL 到下一次 OK。另記各操作失敗數、重連數、資料一致性。</p></div>
</div></section>

<section id="hyp"><h2 class="title"><small>03 · HYPOTHESES</small>假設</h2>
<p class="sub">規則只有一條：<b>FE 與 BE 各自要有 2/3 存活</b>。任一層剩 1 個，寫入就停；查詢能不能活，由實驗決定。</p>
{matrix}
<h3>要靠實驗回答的問題</h3>
<ol class="notes">{"".join(f"<li>{inline(q)}</li>" for q in questions)}</ol>
</section>

<section id="scen"><h2 class="title"><small>04 · SCENARIOS</small>情境</h2>
<p class="sub">fault-scenarios delta spec 的 {n_sc} 個 Scenario：注入條件與預期。</p>
{"".join(scen_html)}
</section>

<section id="appendix"><h2 class="title"><small>APPENDIX</small>OpenSpec 原文</h2>
<p class="sub">主 spec 是環境、工具與故障情境的行為契約（change fault-matrix 已 archive 併入）；proposal / design / tasks 是這次實驗的完整記錄。展開才看。</p>
{"".join(appendix)}
</section>
</main></div></div>'''

EXTRA = """<style>
.figure{--paper:#fff;--rule:#d9eee8;--rule-solid:#d9eee8;--accent:#11a679;--accent-tint:rgba(17,166,121,.10);--white:#fff;--ink-05:rgba(15,26,20,.05);--ink-02:rgba(15,26,20,.02);--ink-20:rgba(15,26,20,.20);--ink-30:rgba(15,26,20,.30);--muted-10:rgba(79,94,86,.10);--muted-15:rgba(79,94,86,.15);--link:#0b7a58}
.cards.method{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.hyp td .note,.scen-table td .note{display:block;font-size:12px;color:var(--muted);margin-top:4px}
.hyp td{white-space:nowrap} .hyp td:first-child{white-space:normal;min-width:140px}
.scen-table td:first-child{min-width:160px} .scen-table td:last-child,.scen-table th:last-child{white-space:nowrap}
table.mini{border:0;background:transparent;font-size:13px} table.mini td{padding:5px 6px 5px 0;border-bottom:1px solid var(--border)} table.mini tr:last-child td{border-bottom:0}
.card p{margin:0;font-size:14px;color:var(--ink-soft)}
details{border:1px solid var(--border);border-radius:12px;background:#fff;margin:10px 0} summary{cursor:pointer;padding:12px 16px;font-weight:600;font-size:14px;list-style:none;display:flex;gap:10px;align-items:center} summary::before{content:"+";font-family:var(--mono);color:var(--primary-deep);width:14px} details[open] summary::before{content:"−"} details[open] summary{border-bottom:1px solid var(--border)} details .doc{padding:4px 16px 12px}
.side .sub-link{font-size:12px;padding-left:16px}
ol.notes li{margin-bottom:6px}
</style>"""
OUT.write_text(shell("Doris HA 實驗設計", "Doris 三節點 HA 故障矩陣的實驗設計：架構圖、注入方式、量測定義、預期矩陣與每個情境的假設。", body, "specs", EXTRA), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes): {n_cells} cells, {n_sc} scenarios, {len(main_specs)} main specs in appendix")
