#!/usr/bin/env python3
"""Build site/results.html (實驗過程與全部結果) from results/summary.json + per-run logs.
Also copies the per-run probe logs into site/results/ so the deployed page can link to them.
Run after experiments/fill_results.py:  ./venv/bin/python site/build_results.py"""
import json, markdown, pathlib, shutil, html, re, collections, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, steps, lvl, plain
import yaml

def md(t): return markdown.markdown(t)
ROOT = pathlib.Path(__file__).resolve().parent.parent
agg = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
order = [s["id"] for s in yaml.safe_load((ROOT / "experiments/scenarios.yaml").read_text(encoding="utf-8"))["scenarios"]]
SITE_RES = ROOT / "site/results"

def copy_logs():
    if SITE_RES.exists(): shutil.rmtree(SITE_RES)
    for f in ROOT.glob("results/pass-*/*/*.log"):
        if f.parent.parent.name == "pass-0": continue
        dst = SITE_RES / f.parent.parent.name / f.parent.name / f.name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
    for f in ROOT.glob("results/pass-*/*/summary.json"):
        dst = SITE_RES / f.parent.parent.name / f.parent.name / f.name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
copy_logs()

GROUPS = [("vm", "壞一個元件 · 整台 VM 關機", lambda i: i.startswith("vm-")), ("fe", "壞一個元件 · FE 程序", lambda i: i.startswith("fe-")),
          ("be", "壞一個元件 · BE 程序", lambda i: i.startswith("be-")), ("double", "同時壞兩個以上", lambda i: i.startswith("double-"))]

def timeline(events, windows):
    items = []
    for e in events:
        items.append((e[:8], f'<div class="t">{e[:8]}</div><div class="e ev">{html.escape(e[9:])}</div>'))
    for w in windows or []:
        items.append((w["start"], f'<div class="t">{w["start"]}</div><div class="e ko">client 失敗開始 → {w["end"] or "?"} 恢復（{w["secs"]} 秒）</div>'))
    items.sort(key=lambda x: x[0])
    return '<div class="timeline">' + "".join(h for _, h in items) + "</div>"

def scenario_block(sid):
    a = agg[sid]
    head = f'''<div class="card" id="{sid}"><div class="k">{sid} · {html.escape(" → ".join(a["steps"]))}{(" · client 先連 " + a["order"].replace("-first", "")) if a.get("order") else ""}</div>
    <h4>{html.escape(plain(a["scenario"]))}</h4>
    <p class="muted" style="margin:4px 0 12px">3 輪最差：{lvl(a["overall"])}　arrow-flight：{lvl(a["clients"]["flight"]["worst"])}
    　中斷 mysql {a["clients"]["mysql"]["impact_min"]}～{a["clients"]["mysql"]["impact_max"]}s · jdbc {a["clients"]["jdbc"]["impact_min"]}～{a["clients"]["jdbc"]["impact_max"]}s · flight {a["clients"]["flight"]["impact_min"]}～{a["clients"]["flight"]["impact_max"]}s</p>'''
    rows = []
    for i, p in enumerate(a["passes"]):
        d = a["dirs"][i].replace("results/", "results/")
        cells = []
        for c in ("mysql", "jdbc", "flight"):
            cp = a["clients"][c]["passes"][i]
            fb = ", ".join(f"{k}×{v}" for k, v in (cp["failed_by_type"] or {}).items())
            cells.append(f'<td>{lvl(cp["level"])}<div class="mono" style="font-size:12px;margin-top:4px">中斷 {cp["impact"]}s（失敗 {cp.get("fail_secs")}s + 無回應 {cp.get("stall")}s，最長間隔 {cp.get("max_gap")}s）· 失敗 {cp["failed"]}{(" (" + fb + ")") if fb else ""} · 重連 {cp["reconnects"]}</div><div style="font-size:12px;margin-top:2px"><a href="{d}/{c}.log">log</a></div></td>')
        r = a["recovery"][i]
        rows.append(f'<tr><td class="n">第 {p} 輪</td>{"".join(cells)}<td class="n">{r["restore_secs"] if r["restore_secs"] is not None else "—"}s{(" · systemd +" + str(r["systemd_secs"]) + "s") if r["systemd_secs"] is not None else ""}<div class="muted" style="font-size:11px;white-space:normal">{html.escape(str(r["alive_during"] or ""))[:60]}</div></td></tr>')
    table = f'<div class="tablewrap"><table><thead><tr><th>輪次</th><th>mysql</th><th>jdbc</th><th>arrow-flight</th><th>restore → 健康</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    # timeline of pass 1 (mysql events + windows)
    first = a["clients"]["mysql"]["passes"][0]
    ev = []
    try:
        sj = json.loads((ROOT / a["dirs"][0] / "summary.json").read_text(encoding="utf-8")); ev = sj["after"].get("mysql", {}).get("events") or []
    except Exception: pass
    tl = f'<details style="margin-top:10px"><summary class="mono" style="cursor:pointer;font-size:12px;color:var(--primary-deep)">第 {a["passes"][0]} 輪時間軸（mysql client）</summary>{timeline(ev, first["windows"])}</details>' if ev else ""
    return head + table + tl + "</div>"

sections = []
for key, title, pred in GROUPS:
    ids = [i for i in order if pred(i) and i in agg]
    if not ids: continue
    sections.append(f'<section id="g-{key}"><h2 class="title"><small>{key.upper()}</small>{title}</h2><div class="cards" style="grid-template-columns:1fr">{"".join(scenario_block(i) for i in ids)}</div></section>')

n_runs = sum(len(a["passes"]) for a in agg.values())
notes_md = (ROOT / "results/run-notes.md"); run_notes = ("<section class=\"tight\"><h2 class=\"title\"><small>THIS RUN</small>本次執行備註</h2>" + md(notes_md.read_text(encoding="utf-8")).replace("<ul>", "<ul class=\"notes\">") + "</section>") if notes_md.exists() else ""
body = f'''<div class="hero"><div class="container">{steps("results")}<p class="eyebrow">Step 03 · 實驗過程與全部結果</p>
<h1 class="display">每一格、每一輪、<em>每個 client</em> 的原始結果</h1>
<p class="lede">依 <a href="specs.html">實驗設計</a> 的故障矩陣，由 <code>experiments/run_matrix.py</code> 自動逐格執行：<b>monitor → 健康跑 30 秒 → break → 觀察 90～120 秒 → measure → restore → 等叢集健康 → measure</b>。每格跑 3 輪，每輪從全部 VM 重新開機開始。共 {len(agg)} 格、{n_runs} 次執行。結果等級由 <code>measure</code> 依故障期間最後 30 秒的成功率判定；中斷秒數 = 失敗時間 + 無回應時間。</p>
<p><a class="btn ghost" href="index.html">← 精簡報告</a></p></div></div>
<div class="container">
<section class="tight"><h2 class="title"><small>HOW TO READ</small>怎麼看這頁</h2>
<div class="cards">
<div class="card"><div class="k">結果等級</div><p style="margin:0">{lvl("rw")} 中斷後讀寫都恢復　{lvl("ro")} 能查、不能寫　{lvl("down")} 查詢也失敗　{lvl("stalled")} 卡住等 timeout，最後 30 秒沒有任何操作完成。arrow-flight 只能查詢：{lvl("read-ok")} / {lvl("read-down")} / {lvl("read-stalled")}</p></div>
<div class="card"><div class="k">中斷秒數</div><p style="margin:0">失敗時間（第一次 FAIL 到下一次 OK）＋無回應時間（連續兩次操作間隔超過 5 秒，例如 master FE hang 時 client 在等 timeout）。含 client 自己的 timeout：connect 3 秒、read / write 8 秒。</p></div>
<div class="card"><div class="k">restore → 健康</div><p style="margin:0">從還原第一個故障到 3 FE / 3 BE 全部 alive、12 個 replica 正常的秒數；crash 類另記 systemd 重啟的秒數。</p></div>
</div></section>
{run_notes}
{"".join(sections)}
</div>'''
out = ROOT / "site/results.html"
out.write_text(shell("Doris HA 實驗結果", "Doris 三節點故障矩陣的完整實驗結果：每格三輪、三個 client、時間軸與原始 log。", body, "results"), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes), {len(agg)} scenarios, logs copied to site/results/")
