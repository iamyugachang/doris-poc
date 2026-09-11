#!/usr/bin/env python3
"""Build site/index.html — the condensed report (matrix + conclusions) from results/summary.json.
Run after fill_results.py:  ./venv/bin/python site/build_index.py"""
import json, pathlib, re, html, sys, datetime, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, steps, lvl
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
agg = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
cfg = yaml.safe_load((ROOT / "experiments/scenarios.yaml").read_text(encoding="utf-8"))
order = [s["id"] for s in cfg["scenarios"]]
ids = [i for i in order if i in agg]
single = [i for i in ids if not i.startswith("double-")]; double = [i for i in ids if i.startswith("double-")]
ZH = {"rw": "讀寫正常", "ro": "只讀", "down": "不可用", "stalled": "卡住（無回應）"}

def impact_range(a, c):
    x, y = a["clients"][c]["impact_min"], a["clients"][c]["impact_max"]
    return "—" if x is None else (f"{x}s" if x == y else f"{x}～{y}s")

# ---- headline numbers
counts = collections.Counter(agg[i]["overall"] for i in ids)
worst_single = max(((agg[i]["clients"]["mysql"]["impact_max"] or 0, i) for i in single), default=(0, None))
best_single = min(((agg[i]["clients"]["jdbc"]["impact_max"] if agg[i]["clients"]["jdbc"]["impact_max"] is not None else 999, i) for i in single), default=(0, None))
verify_fail = 0; total_ops = 0
for f in ROOT.glob("results/pass-[1-9]/*/*.log"):
    t = f.read_text(encoding="utf-8", errors="replace"); verify_fail += t.count("verify id="); total_ops += len(re.findall(r"#\d+ (?:OK|FAIL) ", t))
n_runs = sum(len(agg[i]["passes"]) for i in ids)
restore_secs = [r["restore_secs"] for i in ids for r in agg[i]["recovery"] if r["restore_secs"]]

# ---- matrix table
def label(i):
    steps_ = agg[i]["steps"]; parts = []
    for s in steps_:
        m = dict(re.findall(r"--(\w+) (\S+)", s)); parts.append(f'{m.get("target","vm").upper()} {m.get("mode","stop")} @ {m.get("on","master")}')
    return " + ".join(parts)
rows = []
for i in ids:
    a = agg[i]
    rows.append(f'<tr><td>{html.escape(a["scenario"])}<span class="id">{i}{(" · client " + a["order"]) if a.get("order") else ""}</span></td>'
                f'<td class="mono" style="font-size:12px">{html.escape(label(i))}</td>'
                f'<td>{lvl(a["clients"]["mysql"]["worst"])}<div class="mono" style="font-size:11px;margin-top:3px">{impact_range(a,"mysql")}</div></td>'
                f'<td>{lvl(a["clients"]["jdbc"]["worst"])}<div class="mono" style="font-size:11px;margin-top:3px">{impact_range(a,"jdbc")}</div></td>'
                f'<td>{lvl(a["clients"]["flight"]["worst"])}<div class="mono" style="font-size:11px;margin-top:3px">{impact_range(a,"flight")}</div></td>'
                f'<td>{lvl(a["overall"])}</td></tr>')
matrix = f'<div class="tablewrap"><table class="matrix"><thead><tr><th>情境</th><th>注入</th><th>mysql</th><th>jdbc</th><th>arrow-flight</th><th>結論（三輪最差）</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'

# ---- timeline SVG for a representative run (vm-stop-3clients, first pass, mysql)
def timeline_svg():
    sid = "vm-stop-3clients" if "vm-stop-3clients" in agg else ids[0]
    a = agg[sid]; d = ROOT / a["dirs"][0]
    sj = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    ev = sj["after"]["mysql"]["events"]; win = sj["after"]["mysql"]["windows"]
    t = lambda s: datetime.datetime.strptime(s[:8], "%H:%M:%S")
    pts = [(t(e), e[9:]) for e in ev]
    for w in win:
        pts.append((t(w["start"]), f"client 失敗（{w['secs']}s 後恢復）")); pts.append((t(w["end"]), "client 恢復"))
    pts.sort(); t0 = pts[0][0]; span = max(1, (pts[-1][0] - t0).seconds)
    W, L, R = 960, 64, 896; px = lambda dt: L + int((dt - t0).seconds / span * (R - L) / 4) * 4
    out = [f'<svg viewBox="0 0 960 232" role="img" aria-labelledby="tl-t tl-d" xmlns="http://www.w3.org/2000/svg"><title id="tl-t">{html.escape(a["scenario"])}第 {a["passes"][0]} 輪時間軸</title><desc id="tl-d">從注入故障到 client 恢復與叢集歸隊的事件時間軸。</desc>',
           '<rect width="100%" height="100%" fill="#fff"/>']
    for w in win:
        out.append(f'<rect x="{px(t(w["start"]))}" y="112" width="{max(8, px(t(w["end"])) - px(t(w["start"])))}" height="16" fill="rgba(17,166,121,.15)"/>')
    out.append('<line x1="64" y1="120" x2="896" y2="120" stroke="#d9eee8" stroke-width="1"/>')
    for k in range(0, span + 1, max(15, (span // 5) // 15 * 15 or 15)):
        x = L + int(k / span * (R - L) / 4) * 4
        out.append(f'<line x1="{x}" y1="128" x2="{x}" y2="136" stroke="#7f8f86" stroke-width="0.8"/><text x="{x}" y="148" font-family="JetBrains Mono,monospace" font-size="8" fill="#7f8f86" text-anchor="middle">+{k}s</text>')
    up = True; y_up = [48, 84]; y_dn = [164, 200]; k_up = k_dn = 0
    for dt, msg in pts:
        x = px(dt); focal = "恢復" in msg and "client" in msg
        r = 6 if focal else 4; fill = "#11a679" if focal else ("#d9483b" if "失敗" in msg else "#4f5e56")
        out.append(f'<circle cx="{x}" cy="120" r="{r}" fill="{fill}"/>')
        if up:
            y = y_up[k_up % 2]; k_up += 1; out.append(f'<line x1="{x}" y1="{y+8}" x2="{x}" y2="116" stroke="#d9eee8"/>'); ty = y
        else:
            y = y_dn[k_dn % 2]; k_dn += 1; out.append(f'<line x1="{x}" y1="124" x2="{x}" y2="{y-12}" stroke="#d9eee8"/>'); ty = y
        anchor = "end" if x > 700 else "start"
        out.append(f'<text x="{x}" y="{ty}" font-family="Inter,Noto Sans TC,sans-serif" font-size="11" font-weight="600" fill="{"#0b7a58" if focal else "#0f1a14"}" text-anchor="{anchor}">{html.escape(msg[:44])}</text><text x="{x}" y="{ty+12}" font-family="JetBrains Mono,monospace" font-size="8" fill="#7f8f86" text-anchor="{anchor}">+{(dt-t0).seconds}s · {dt.strftime("%H:%M:%S")}</text>')
        up = not up
    out.append("</svg>"); return "".join(out), a, sj

tl_svg, tl_a, tl_sj = timeline_svg()
diag = {n: (ROOT / f"site/diagrams/{n}.svg").read_text(encoding="utf-8") for n in ("arch-normal", "arch-down")}
svg_vars = '<style>.figure{--paper:#fff;--rule:#d9eee8;--rule-solid:#d9eee8;--accent:#11a679;--accent-tint:rgba(17,166,121,.10);--white:#fff;--ink-05:rgba(15,26,20,.05);--ink-02:rgba(15,26,20,.02);--ink-20:rgba(15,26,20,.20);--ink-30:rgba(15,26,20,.30);--muted-10:rgba(79,94,86,.10);--muted-15:rgba(79,94,86,.15);--link:#0b7a58}</style>'

# ---- conclusions (data-driven sentences)
def zh_list(xs): return "、".join(xs)
single_rw = [i for i in single if agg[i]["overall"] == "rw"]; single_not = [i for i in single if agg[i]["overall"] != "rw"]
double_desc = "；".join(f'{agg[i]["scenario"].split("（")[0]}→{ZH.get(agg[i]["overall"], agg[i]["overall"])}（flight {agg[i]["clients"]["flight"]["worst_zh"]}）' for i in double)
concl = [
  f'<li><b>單一故障（{len(single)} 格）：</b>{len(single_rw)} 格讀寫正常' + (f'，{len(single_not)} 格不是（{zh_list(agg[i]["scenario"] for i in single_not)}）' if single_not else '') + f'。mysql 中斷最長 {worst_single[0]}s（{agg[worst_single[1]]["scenario"] if worst_single[1] else ""}）。</li>',
  f'<li><b>雙重故障（{len(double)} 格）：</b>{double_desc}。等級由 FE 與 BE 各自的多數決決定：任一層剩 1/3，寫入就停。</li>' if double else "",
  f'<li><b>資料一致性：</b>{n_runs} 次執行、{total_ops:,} 次操作，SELECT 驗證不一致 {verify_fail} 次。寫入在中斷視窗內失敗會換新 key 重來，不留下半套資料。</li>',
  f'<li><b>恢復：</b>restore 到 3 FE / 3 BE 全 alive、12 副本 OK，{min(restore_secs) if restore_secs else "—"}～{max(restore_secs) if restore_secs else "—"} 秒（含 VM 開機），不需人工介入。</li>',
  '<li><b>Arrow Flight SQL：</b>Doris 4.1.1 只走查詢，INSERT/DELETE 回 <code>getMysqlChannel not in mysql connection</code>；寫入請用 MySQL 協定或 Stream Load。</li>',
  '<li><b>client 端建議：</b>JDBC 多主機 URL 最省事；自行實作時逾時設 2～3 秒、失敗重連時輪替主機，避免卡在轉發給已死 master 的 follower 上。</li>',
]
stats = f'''<div class="stats">
<div class="stat focal"><div class="k">單一故障讀寫正常</div><div class="v">{len(single_rw)} / {len(single)}</div><div class="d">FE 或 BE 掛一個、整台 VM 停機，client 都在幾秒內恢復</div></div>
<div class="stat"><div class="k">雙重故障</div><div class="v">{counts.get("ro",0)} 只讀 · {counts.get("down",0)+counts.get("stalled",0)} 不可用/卡住</div><div class="d">任一層剩 1/3 就失去寫入；查詢視 FE 是否還能服務</div></div>
<div class="stat"><div class="k">資料不一致</div><div class="v">{verify_fail}</div><div class="d">{n_runs} 次執行 · {total_ops:,} 次操作的 SELECT 驗證</div></div>
<div class="stat"><div class="k">中斷（單一故障）</div><div class="v">{best_single[0] if best_single[1] else "—"}～{worst_single[0]}s</div><div class="d">jdbc 最快、hang 類最慢；含 client 逾時等待</div></div>
</div>'''

body = f'''<div class="hero"><div class="container">{steps("index")}<p class="eyebrow">Step 01 · 精簡報告 · Apache Doris 4.1.1 · GCP asia-east1 三個 zone</p>
<h1 class="display">FE 掛了、BE 掛了、整台 VM 掛了，<em>client 還能寫嗎？</em></h1>
<p class="lede">三台 VM 各跑一個 FE 與一個 BE，client 每秒對同一把 key 做 <b>INSERT → UPSERT → SELECT → DELETE → SELECT</b>，同時用 mysql / jdbc / arrow-flight 三種協定。我們把 {len(ids)} 種故障各注入三輪，量 client 中斷幾秒、寫入還能不能成功、資料有沒有不一致。</p>
<p><a class="btn" href="specs.html">02 實驗設計 →</a> <a class="btn ghost" href="results.html">03 過程與全部結果 →</a></p></div></div>
<div class="container">
<section class="tight">{stats}</section>
<section id="matrix"><h2 class="title"><small>RESULT MATRIX</small>故障矩陣（{len(ids)} 格 × 3 輪）</h2>
<p class="sub">等級取三輪中最差；秒數是三輪的影響範圍＝失敗視窗（第一次失敗到下一次成功）＋卡頓（連續兩次操作間隔超過 5 秒）。arrow-flight 只做查詢，所以只有讀取正常 / 讀取失敗。點 <a href="results.html">03</a> 看每一輪、每個 client 的原始 log。</p>{matrix}</section>
<section id="conclusions"><h2 class="title"><small>TAKEAWAYS</small>結論</h2><ul class="notes">{"".join(concl)}</ul></section>
<section id="arch"><h2 class="title"><small>ARCHITECTURE</small>正常狀態 vs 掛掉一台</h2>
<p class="sub">3 個 FE 都是 FOLLOWER，以多數決選出 1 個 master；3 個 BE 是一個資料池，每個 tablet 三副本各放一個 zone。client 帶三台 FE 的主機清單，第一台連不上就試下一台。</p>
<div class="grid2"><figure><div class="figure">{diag["arch-normal"]}</div><figcaption>正常：client 連在當下的 master，follower 透過 edit log 同步。</figcaption></figure>
<figure><div class="figure">{diag["arch-down"]}</div><figcaption>掛掉一台：連線被重設後改連他台，剩餘 FE 選出新 master，副本剩 2/3 仍可讀寫。</figcaption></figure></div></section>
<section id="timeline"><h2 class="title"><small>ONE RUN</small>一次故障的時間軸</h2>
<p class="sub">{html.escape(tl_a["scenario"])}，第 {tl_a["passes"][0]} 輪，mysql client 視角。橘/綠帶是 client 受影響的區間。</p>
<figure><div class="figure">{tl_svg}</div><figcaption>來源：<code>{tl_a["dirs"][0]}/mysql.log</code>，由 measure 的 EVENT 與失敗視窗產生。</figcaption></figure></section>
<section id="repro"><h2 class="title"><small>REPRODUCE</small>自己跑一次</h2>
<div class="grid2"><div class="tablewrap"><table><thead><tr><th>階段</th><th>指令</th><th>做什麼</th></tr></thead><tbody>
<tr><td>建立</td><td><code>./demo.sh up</code></td><td>terraform apply（4 VM + 防火牆）→ ansible（Doris、叢集、三個探測）→ 灌資料</td></tr>
<tr><td>監控</td><td><code>./demo.sh monitor</code></td><td>在 client VM 起三個探測並即時合併捲動</td></tr>
<tr><td>斷線</td><td><code>./demo.sh break --target fe|be|vm --mode crash|dead|hang|stop --on master|follower</code></td><td>注入故障，可疊加</td></tr>
<tr><td>復原</td><td><code>./demo.sh restore</code></td><td>逆序逆轉全部故障，等叢集健康</td></tr>
<tr><td>測量</td><td><code>./demo.sh measure</code></td><td>中斷視窗、失敗數、可用性等級</td></tr>
<tr><td>整個矩陣</td><td><code>experiments/run_matrix.py --pass N</code></td><td>開機 → 逐格跑 → 關機；結果進 results/</td></tr>
<tr><td>Tear down</td><td><code>./demo.sh down</code></td><td>terraform destroy</td></tr></tbody></table></div>
<div><div class="tablewrap"><table><thead><tr><th>成本（asia-east1）</th><th>金額</th></tr></thead><tbody>
<tr><td>3 × e2-standard-4 + client e2-small + 170 GB pd-balanced，運行中</td><td class="n">約 US$0.51 / 小時</td></tr>
<tr><td>跑完三輪矩陣（約 4 小時）</td><td class="n">約 US$2</td></tr>
<tr><td><code>stop</code> 後只剩磁碟</td><td class="n">約 US$16 / 月</td></tr>
<tr><td><code>down</code> 後</td><td class="n">0</td></tr></tbody></table></div>
<p style="margin:16px 0 0"><a class="btn" href="explore.html">打開互動架構圖 ↗</a></p></div></div></section>
</div>'''
out = ROOT / "site/index.html"
out.write_text(shell("Doris 三節點 HA 實測", "Apache Doris 4.1.1 在 GCP 三個 zone 的故障矩陣實驗：FE/BE/VM 的 crash、dead、hang、stop 與雙重故障下，三種 client 的中斷秒數與可用性等級。", body, "index", svg_vars), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes): {len(ids)} scenarios, {n_runs} runs, verify failures {verify_fail}")
