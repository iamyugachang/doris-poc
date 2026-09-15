#!/usr/bin/env python3
"""Build site/index.html — the condensed report (matrix + conclusions) from results/summary.json.
Run after fill_results.py:  ./venv/bin/python site/build_index.py"""
import json, pathlib, re, html, sys, datetime, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from theme import shell, steps, lvl, plain
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
counts = collections.Counter(agg[i]["overall"] for i in double)          # double-fault cells only
single_rw = [i for i in single if agg[i]["overall"] == "rw"]; single_not = [i for i in single if agg[i]["overall"] != "rw"]
CL = ("mysql", "jdbc", "flight")
def rng(cells):
    lo = min((agg[i]["clients"][c]["impact_min"] for i in cells for c in CL if agg[i]["clients"][c]["impact_min"] is not None), default=None)
    hi = max((agg[i]["clients"][c]["impact_max"] for i in cells for c in CL if agg[i]["clients"][c]["impact_max"] is not None), default=None)
    return lo, hi
ok_lo, ok_hi = rng(single_rw); bad_lo, bad_hi = rng(single_not)          # 11 normal cells vs the exception(s)
worst_single = max(((agg[i]["clients"]["mysql"]["impact_max"] or 0, i) for i in single), default=(0, None))
verify_fail = 0; total_ops = 0
for f in ROOT.glob("results/pass-[1-9]/*/*.log"):
    t = f.read_text(encoding="utf-8", errors="replace"); verify_fail += t.count("verify id="); total_ops += len(re.findall(r"#\d+ (?:OK|FAIL) ", t))
n_runs = sum(len(agg[i]["passes"]) for i in ids)
restore_secs = [r["restore_secs"] for i in ids for r in agg[i]["recovery"] if r["restore_secs"]]

# ---- matrix table (grouped: 壞一個元件 → VM / FE / BE；同時壞兩個以上)
def label(i):
    parts = []
    for st in agg[i]["steps"]:
        m = dict(re.findall(r"--(\w+) (\S+)", st)); parts.append(f'{m.get("target","vm").upper()} {m.get("mode","stop")} @ {m.get("on","master")}')
    return " + ".join(parts)
GROUPS = [("壞一個元件 · 整台 VM 關機", lambda i: i.startswith("vm-")), ("壞一個元件 · FE 程序", lambda i: i.startswith("fe-")),
          ("壞一個元件 · BE 程序", lambda i: i.startswith("be-")), ("同時壞兩個以上（quorum 邊界）", lambda i: i.startswith("double-"))]
rows = []
for title, pred in GROUPS:
    gids = [i for i in ids if pred(i)]
    if not gids: continue
    rows.append(f'<tr class="grp"><td colspan="6">{title}（{len(gids)} 格）</td></tr>')
    for i in gids:
        a = agg[i]
        rows.append(f'<tr><td>{html.escape(plain(a["scenario"]))}<span class="id">{i}{(" · client 先連 " + a["order"].replace("-first", "")) if a.get("order") else ""}</span></td>'
                    f'<td class="mono" style="font-size:12px">{html.escape(label(i))}</td>'
                    + "".join(f'<td>{lvl(a["clients"][c]["worst"])}<div class="mono" style="font-size:11px;margin-top:3px">{impact_range(a,c)}</div></td>' for c in CL)
                    + f'<td>{lvl(a["overall"])}</td></tr>')
matrix = f'<div class="tablewrap"><table class="matrix"><thead><tr><th>情境</th><th>怎麼壞 · 壞哪台</th><th>mysql</th><th>jdbc</th><th>arrow-flight</th><th>結果（3 輪最差）</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
legend = f'''<div class="legend"><div><b>怎麼壞</b>　<span class="mono">crash</span> = kill -9，systemd 10 秒內自動重啟　<span class="mono">dead</span> = systemctl stop，不會自己起來　<span class="mono">hang</span> = kill -STOP 凍結，程序在、port 在、不回應　<span class="mono">stop</span> = 整台 VM 關機</div>
<div><b>壞哪台</b>　<span class="mono">master</span> = 當下被選為 leader 的 FE 所在的 VM　<span class="mono">follower</span> = 其他兩台　（BE 沒有 master 概念，這裡指「跟 master FE 同一台 / 不同台」的 BE）</div>
<div><b>結果</b>　{lvl("rw")} 中斷後讀寫都恢復　{lvl("ro")} 能查、不能寫　{lvl("down")} 查詢也失敗　{lvl("stalled")} 卡住等 timeout　（arrow-flight 只能查詢：{lvl("read-ok")} / {lvl("read-down")} / {lvl("read-stalled")}）</div></div>'''

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
    out = [f'<svg viewBox="0 0 960 232" role="img" aria-labelledby="tl-t tl-d" xmlns="http://www.w3.org/2000/svg"><title id="tl-t">{html.escape(a["scenario"])}第 {a["passes"][0]} 輪時間軸</title><desc id="tl-d">從製造故障到 client 恢復、叢集回到健康的事件時間軸。</desc>',
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
(ROOT / "site/diagrams/timeline.svg").write_text(tl_svg, encoding="utf-8")
diag = {n: (ROOT / f"site/diagrams/{n}.svg").read_text(encoding="utf-8") for n in ("arch-normal", "arch-down")}
svg_vars = '<style>.figure{--paper:#fff;--rule:#d9eee8;--rule-solid:#d9eee8;--accent:#11a679;--accent-tint:rgba(17,166,121,.10);--white:#fff;--ink-05:rgba(15,26,20,.05);--ink-02:rgba(15,26,20,.02);--ink-20:rgba(15,26,20,.20);--ink-30:rgba(15,26,20,.30);--muted-10:rgba(79,94,86,.10);--muted-15:rgba(79,94,86,.15);--link:#0b7a58}</style>'

# ---- conclusions (data-driven sentences)
def zh_list(xs): return "、".join(xs)
def short(i): return agg[i]["scenario"].split("（")[0]
double_desc = "；".join(f'{short(i)} → {ZH.get(agg[i]["overall"], agg[i]["overall"])}（arrow-flight {agg[i]["clients"]["flight"]["worst_zh"]}）' for i in double)
hang_note = ""
if "fe-hang-master" in single_not:
    pp = agg["fe-hang-master"]["overall_per_pass"]; n_bad = sum(1 for x in pp if x != "rw")
    hang_note = (f'。<b>例外是 master FE hang</b>：FE 被凍結但 port 還開著，其他 FE 遲遲沒有重新選 master（3 輪裡 {n_bad} 輪在 120 秒觀察期內沒選出來），'
                 f'client 只能讀或整個卡住，中斷 {bad_lo}～{bad_hi} 秒。程序「假死」比「真死」更危險')
concl = [
  f'<li><b>壞一個元件（{len(single)} 格）：</b>{len(single_rw)} 格讀寫正常，client 最慢 {ok_hi} 秒內自己恢復' + hang_note + '。</li>',
  f'<li><b>同時壞兩個以上（{len(double)} 格）：</b>{double_desc}。規則很單純：<b>FE 和 BE 各自要 3 台活 2 台（quorum）才能寫</b>；FE 沒有 quorum 連查詢都不行。</li>' if double else "",
  f'<li><b>資料正確性：</b>{n_runs} 次執行、{total_ops:,} 次操作，每次都用 SELECT 驗證，錯誤 {verify_fail} 筆。寫入失敗就換一把新 key 重新開始，所以不會留下寫一半的資料。</li>',
  f'<li><b>恢復：</b>restore 之後 {min(restore_secs) if restore_secs else "—"}～{max(restore_secs) if restore_secs else "—"} 秒回到 3 FE / 3 BE 全部 alive、12 個 replica 正常（最長的含 VM 開機），不用人工處理。</li>',
  '<li><b>Arrow Flight SQL 只能查詢：</b>Doris 4.1.1 用它做 INSERT / DELETE 會回 <code>getMysqlChannel not in mysql connection</code>。要寫入請走 MySQL 協定或 Stream Load（HTTP 批次匯入）。</li>',
  '<li><b>給應用程式的建議：</b>用 JDBC 多主機連線字串 <code>jdbc:mysql://fe1,fe2,fe3/db</code> 最省事，driver 自動換另一台 FE。自己實作 client 就把 timeout 設 2～3 秒、重連時換下一台 FE。特別注意 hang：連線不會被 reset，client 只會等 timeout，所以 timeout 不能設太長。</li>',
]
stats = f'''<div class="stats">
<div class="stat focal"><div class="k">壞一個元件 · 讀寫正常</div><div class="v">{len(single_rw)} / {len(single)}</div><div class="d">FE、BE 或整台 VM 壞一個，client 最慢 {ok_hi} 秒內自己恢復；例外是 master FE hang</div></div>
<div class="stat"><div class="k">同時壞兩個以上（{len(double)} 格）</div><div class="v">{counts.get("ro",0)} 只讀 · {counts.get("down",0)+counts.get("stalled",0)} 不可用</div><div class="d">FE 或 BE 只剩 1 台活著就不能寫；FE 沒有 quorum 連查詢都不行</div></div>
<div class="stat"><div class="k">資料錯誤</div><div class="v">{verify_fail}</div><div class="d">{n_runs} 次執行 · {total_ops:,} 次操作，每次都用 SELECT 驗證</div></div>
<div class="stat"><div class="k">中斷秒數（壞一個元件）</div><div class="v">{ok_lo}～{ok_hi}s</div><div class="d">{len(single_rw)} 格正常的範圍，含 client 等 timeout 的時間；master FE hang 例外：{bad_lo}～{bad_hi} 秒</div></div>
</div>'''

body = f'''<div class="hero"><div class="container">{steps("index")}<p class="eyebrow">Step 01 · 精簡報告 · Apache Doris 4.1.1 · GCP asia-east1 三個 zone</p>
<h1 class="display">FE 掛了、BE 掛了、整台 VM 掛了，<em>client 還能寫嗎？</em></h1>
<p class="lede">3 台 VM 各跑 1 個 <b>FE</b>（Frontend：接 SQL、管 metadata、選 master）和 1 個 <b>BE</b>（Backend：存資料、算查詢）。client（測試程式）每秒對同一把 key 做 <b>INSERT → UPSERT → SELECT → DELETE → SELECT</b>，同時用 mysql / jdbc / arrow-flight 三種連線方式。{len(ids)} 種故障各做 3 輪，量 client 斷多久、還能不能寫、資料有沒有錯。</p>
<p><a class="btn" href="specs.html">02 實驗設計 →</a> <a class="btn ghost" href="results.html">03 過程與全部結果 →</a></p></div></div>
<div class="container">
<section class="tight">{stats}</section>
<section id="matrix"><h2 class="title"><small>RESULT MATRIX</small>故障矩陣（{len(ids)} 格 × 3 輪）</h2>
<p class="sub">每格做 3 輪，結果取最差的一輪；秒數是 3 輪的中斷範圍。<b>中斷秒數</b> = 失敗時間（第一次 FAIL 到下一次 OK）+ 無回應時間（連續兩次操作間隔超過 5 秒）。點 <a href="results.html">03</a> 看每一輪、每個 client 的原始 log。</p>{legend}{matrix}</section>
<section id="conclusions"><h2 class="title"><small>TAKEAWAYS</small>結論</h2><ul class="notes">{"".join(concl)}</ul><p class="muted" style="font-size:13px;max-width:78ch">本次執行 2026-09-15。當天 asia-east1-c 的 e2-standard-4 缺貨，doris-3 改用 n2 / n2d-standard-4；細節見 <a href="results.html">03</a> 的「本次執行備註」。</p></section>
<section id="arch"><h2 class="title"><small>ARCHITECTURE</small>正常狀態 vs 壞一台</h2>
<p class="sub">3 個 FE 角色都是 FOLLOWER（有投票權），互相選出 1 個 master；3 個 BE 組成一個資料池，每份資料 3 個 replica，各放一個 zone。client 自己帶三台 FE 的清單，第一台連不上就試下一台，不經 Load Balancer。</p>
<div class="grid2"><figure><div class="figure">{diag["arch-normal"]}</div><figcaption>正常：client 連在當下的 master；master 的 metadata 變更透過 edit log（類似 WAL）複製給 follower。</figcaption></figure>
<figure><div class="figure">{diag["arch-down"]}</div><figcaption>壞一台：client 連線被 reset 後換另一台 FE；剩下 2 個 FE 選出新 master；replica 剩 2/3，仍可讀寫。</figcaption></figure></div></section>
<section id="timeline"><h2 class="title"><small>ONE RUN</small>一次故障的時間軸</h2>
<p class="sub">{html.escape(plain(tl_a["scenario"]))}，第 {tl_a["passes"][0]} 輪，mysql client 視角。綠色帶是 client 從失敗到恢復的區間。</p>
<figure><div class="figure">{tl_svg}</div><figcaption>來源：<code>{tl_a["dirs"][0]}/mysql.log</code>，由 measure 從 log 的 EVENT 與失敗區間產生。</figcaption></figure></section>
<section id="repro"><h2 class="title"><small>REPRODUCE</small>自己跑一次</h2>
<div class="grid2"><div class="tablewrap"><table><thead><tr><th>階段</th><th>指令</th><th>做什麼</th></tr></thead><tbody>
<tr><td>建環境</td><td><code>./demo.sh up</code></td><td>terraform apply（4 台 VM + 防火牆）→ ansible（裝 Doris、組叢集、裝三個 probe）→ 灌資料</td></tr>
<tr><td>監控</td><td><code>./demo.sh monitor</code></td><td>在 client VM 啟動三個 probe，並即時合併顯示 log</td></tr>
<tr><td>製造故障</td><td><code>./demo.sh break --target fe|be|vm --mode crash|dead|hang|stop --on master|follower</code></td><td>可連續執行、疊加多個故障</td></tr>
<tr><td>還原</td><td><code>./demo.sh restore</code></td><td>依相反順序還原全部故障，等叢集恢復健康</td></tr>
<tr><td>量測</td><td><code>./demo.sh measure</code></td><td>中斷秒數、失敗數、可用性等級</td></tr>
<tr><td>整個矩陣</td><td><code>experiments/run_matrix.py --pass N</code></td><td>開機 → 逐格跑 → 關機；結果寫進 results/</td></tr>
<tr><td>刪環境</td><td><code>./demo.sh down</code></td><td>terraform destroy</td></tr></tbody></table></div>
<div><div class="tablewrap"><table><thead><tr><th>成本（asia-east1）</th><th>金額</th></tr></thead><tbody>
<tr><td>3 × e2-standard-4 + client e2-small + 170 GB pd-balanced，運行中</td><td class="n">約 US$0.51 / 小時</td></tr>
<tr><td>跑完 3 輪矩陣（約 4 小時）</td><td class="n">約 US$2</td></tr>
<tr><td>VM 關機後只剩磁碟</td><td class="n">約 US$16 / 月</td></tr>
<tr><td><code>down</code> 之後</td><td class="n">0</td></tr></tbody></table></div>
<p style="margin:16px 0 0"><a class="btn" href="explore.html">打開互動架構圖 ↗</a></p></div></div></section>
</div>'''
EXTRA = svg_vars + '<style>.legend{font-size:13px;color:var(--muted);margin:0 0 14px;display:grid;gap:4px} .legend b{color:var(--ink)} .matrix tr.grp td{background:var(--surface);font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--primary-deep);font-weight:700}</style>'
out = ROOT / "site/index.html"
out.write_text(shell("Doris 三節點 HA 實測", "Apache Doris 4.1.1 在 GCP 三個 zone 的故障矩陣實驗：FE/BE/VM 的 crash、dead、hang、stop 與雙重故障下，三種 client 的中斷秒數與可用性等級。", body, "index", EXTRA), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes): {len(ids)} scenarios, {n_runs} runs, verify failures {verify_fail}; single ok {ok_lo}-{ok_hi}s, exception {bad_lo}-{bad_hi}s, double counts {dict(counts)}")
