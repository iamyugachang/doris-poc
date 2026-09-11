#!/usr/bin/env python3
"""Render openspec/ (config context, main specs, active changes) into site/specs.html using the shared Doris theme.
Run: ./venv/bin/python site/build_specs.py"""
import re, html, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, steps
import markdown, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OS = ROOT / "openspec"
OUT = ROOT / "site" / "specs.html"
MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
def md(text): MD.reset(); return MD.convert(text)
def slug(s): return re.sub(r"[^a-z0-9一-鿿]+", "-", s.lower()).strip("-")

def render_spec_body(text):
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
            flush_buf(scen["lines"] if scen else out); flush_req()
            if line.strip() == "## Purpose": out.append('<p class="eyebrow-sm">Purpose</p>')
            continue
        if re.match(r"^# ", line): continue
        (scen["lines"] if scen is not None else buf).append(line)
    flush_buf(scen["lines"] if scen else out); flush_req()
    return "".join(out)

def render_scenario(scen):
    when, then, extra, cur = [], [], [], None
    for l in scen["lines"]:
        s = l.strip()
        if s.startswith("- **WHEN**"): cur = when; when.append(s[len("- **WHEN**"):].strip())
        elif s.startswith("- **THEN**"): cur = then; then.append(s[len("- **THEN**"):].strip())
        elif s.startswith("- 實測"): cur = extra; extra.append(s[2:].strip())
        elif s.startswith("- ") and cur is not None and cur is not extra: cur.append(s[2:].strip())
        elif s: (cur if cur is not None else extra).append(s)
    inline = lambda t: MD.convert(t).replace("<p>", "").replace("</p>", "")
    h = [f'<div class="scen"><div class="scen-name">{html.escape(scen["name"])}</div>']
    if when: h.append(f'<div class="wt"><span class="kw">WHEN</span><div>{"<br>".join(inline(w) for w in when)}</div></div>')
    if then: h.append(f'<div class="wt"><span class="kw then">THEN</span><div>{"<br>".join(inline(t) for t in then)}</div></div>')
    if extra: h.append('<div class="measured">' + "".join(f"<div>✔ {inline(e)}</div>" for e in extra) + "</div>")
    h.append("</div>"); return "".join(h)

def render_tasks(text):
    total = len(re.findall(r"^- \[[ xX]\]", text, re.M)); done = len(re.findall(r"^- \[[xX]\]", text, re.M))
    body = re.sub(r"^- \[ \] (\S+) ", r'- <span class="cb"></span><span class="tid">\1</span> ', text, flags=re.M)
    body = re.sub(r"^- \[[xX]\] (\S+) ", r'- <span class="cb on"></span><span class="tid">\1</span> ', body, flags=re.M)
    pct = int(done * 100 / total) if total else 0
    return f'<div class="progress"><div class="bar" style="width:{pct}%"></div></div><p class="muted">{done} / {total} 完成（{pct}%）</p>' + md(body)

cfg = yaml.safe_load((OS / "config.yaml").read_text(encoding="utf-8"))
context_md = "\n".join(l for l in cfg.get("context", "").splitlines() if not l.startswith("Language:") and "artifacts must be" not in l and "SHALL/MUST" not in l)
rules = cfg.get("rules", {})
specs = [(d.name, (d / "spec.md").read_text(encoding="utf-8")) for d in sorted((OS / "specs").iterdir()) if (d / "spec.md").exists()]
changes = []
for d in sorted((OS / "changes").iterdir()):
    if d.name == "archive" or not d.is_dir(): continue
    c = {"name": d.name}
    for a in ("proposal", "design", "tasks"):
        p = d / f"{a}.md"; c[a] = p.read_text(encoding="utf-8") if p.exists() else ""
    c["deltas"] = [(s.parent.name, s.read_text(encoding="utf-8")) for s in sorted(d.glob("specs/*/spec.md"))]
    changes.append(c)

TITLES = {"topology": "拓撲 topology", "clients": "探測 client clients", "fault-scenarios": "故障情境 fault-scenarios", "operations": "操作契約 operations"}
nav = ['<div class="lbl">目錄</div><a href="#context">專案背景</a>'] + [f'<a href="#spec-{n}">{TITLES.get(n, n)}</a>' for n, _ in specs]
for c in changes:
    nav.append(f'<div class="lbl">change · {c["name"]}</div><a href="#proposal-{c["name"]}">Proposal</a><a href="#design-{c["name"]}">Design</a>' + "".join(f'<a href="#delta-{c["name"]}-{cap}">Delta · {TITLES.get(cap, cap)}</a>' for cap, _ in c["deltas"]) + f'<a href="#tasks-{c["name"]}">Tasks</a>')
nav.append('<div class="lbl">格式</div><span style="padding:4px 8px;color:var(--soft)">Requirement = 行為契約<br>Scenario = WHEN / THEN（預期）<br>綠底 = 實驗後補上的實測</span>')

parts = [f'<section class="doc" id="context"><h2 class="title"><small>CONTEXT</small>專案背景</h2>{md(context_md)}']
if rules: parts.append('<h3>寫作規則</h3>' + md("\n".join(f"- **{k}**：" + "；".join(v) for k, v in rules.items())))
parts.append("</section>")
for n, text in specs:
    n_req = len(re.findall(r"^### Requirement:", text, re.M)); n_sc = len(re.findall(r"^#### Scenario:", text, re.M))
    parts.append(f'<section class="doc" id="spec-{n}"><h2 class="title"><small>SPEC</small>{TITLES.get(n, n)}</h2><p class="muted">{n_req} 個 Requirement · {n_sc} 個 Scenario · 環境與工具的行為契約</p>{render_spec_body(text)}</section>')
for c in changes:
    parts.append(f'<section class="doc" id="change-{c["name"]}"><h2 class="title"><small>CHANGE</small>{c["name"]}</h2><p class="muted">實驗提案：為什麼、要做什麼、怎麼做、預期什麼、任務清單。每個 Scenario 的綠底段落是實驗跑完後由工具回填的實測。</p>')
    parts.append(f'<h3 id="proposal-{c["name"]}">Proposal</h3>' + md(c["proposal"]))
    parts.append(f'<h3 id="design-{c["name"]}">Design</h3>' + md(c["design"]))
    for cap, text in c["deltas"]:
        n_sc = len(re.findall(r"^#### Scenario:", text, re.M)); n_m = len(re.findall(r"^- 實測", text, re.M))
        parts.append(f'<h3 id="delta-{c["name"]}-{cap}">Delta spec · {TITLES.get(cap, cap)} <span class="muted">（{n_sc} 個 Scenario{"，" + str(n_m) + " 條實測" if n_m else ""}）</span></h3>{render_spec_body(text)}')
    parts.append(f'<h3 id="tasks-{c["name"]}">Tasks</h3>' + render_tasks(c["tasks"]) + "</section>")

body = f'''<div class="hero"><div class="container">{steps("specs")}<p class="eyebrow">Step 02 · 實驗設計（OpenSpec）</p>
<h1 class="display">先講清楚<em>要驗證什麼</em>，再動手</h1>
<p class="lede">主 spec 是環境與工具的行為契約；change <b>fault-matrix</b> 是實驗設計：故障矩陣的每一格是一個 Scenario，寫明注入方式、觀察點與預期的可用性等級（讀寫正常 / 只讀 / 不可用）。實驗依 tasks 逐格跑完後，工具把三輪實測回填到各 Scenario。</p>
<p><a class="btn" href="results.html">看實驗過程與結果 →</a> <a class="btn ghost" href="index.html">← 精簡報告</a></p></div></div>
<div class="container"><div class="layout"><nav class="side">{"".join(nav)}</nav><main>{"".join(parts)}</main></div></div>'''
OUT.write_text(shell("Doris HA 實驗設計", "Doris 三節點 HA 實驗的 OpenSpec 規格：專案背景、環境契約、故障矩陣提案、設計、預期與任務清單。", body, "specs"), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes): {len(specs)} specs, {len(changes)} changes")
