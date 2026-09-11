"""Shared look for the three demo pages, modelled on doris.apache.org (default 'doris' theme):
cream paper, ink green-black, primary green #11a679, yellow accent #ffd23f, Inter body, JetBrains Mono
uppercase display titles, 4px buttons, soft green borders. Light only (no dark mode by request)."""
import datetime

SITE_URL = "https://doris-ha-demo-195642473078.asia-east1.run.app"
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap">'

CSS = """
:root{--paper:#fffcf5;--cream:#f5efe4;--cream-light:#faf6ee;--ink:#0f1a14;--ink-soft:#1b2a22;--muted:#4f5e56;--soft:#7f8f86;
  --primary:#11a679;--primary-deep:#0b7a58;--primary-dark:#06805f;--primary-tint:#e8faf5;--primary-soft:#c9ffe6;--primary-glow:#2ddfa8;
  --accent:#ffd23f;--accent-soft:#fff6cc;--border:#d9eee8;--surface:#f4fbf8;--note:#e8faf5;--footer:#0c1613;
  --danger:#d9483b;--danger-soft:#ffe2dd;--warn:#b7791f;--warn-soft:#fff1c2;
  --sans:"Inter","Noto Sans TC",-apple-system,"Segoe UI","Helvetica Neue",Arial,sans-serif;--mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color-scheme:light}
*{box-sizing:border-box} html{background:var(--paper)}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.65;padding-block:0 0;padding-inline:0}
a{color:var(--primary-deep);text-decoration:none} a:hover{text-decoration:underline}
.container{max-width:1120px;margin:0 auto;padding-inline:clamp(16px,4vw,40px)}
header.top{position:sticky;top:0;z-index:5;background:rgba(255,252,245,.92);backdrop-filter:blur(6px);border-bottom:1px solid var(--border)}
header.top .container{display:flex;justify-content:space-between;align-items:center;gap:24px;height:64px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);font-weight:600}
.brand i{width:12px;height:12px;background:var(--primary);border-radius:3px;display:inline-block;box-shadow:3px 3px 0 var(--accent)}
nav.links{display:flex;gap:6px;flex-wrap:wrap} nav.links a{color:var(--ink);font-size:13px;font-weight:500;padding:6px 10px;border-radius:4px} nav.links a:hover{background:var(--surface);text-decoration:none} nav.links a.cur{background:var(--primary);color:#fff}
.hero{padding-block:56px 40px;background:linear-gradient(180deg,var(--cream-light),var(--paper))}
.hero .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--primary-deep);margin:0 0 14px;font-weight:600}
.display{font-family:var(--mono);text-transform:uppercase;letter-spacing:-.035em;word-spacing:-.18em;font-weight:700;line-height:.95;margin:0 0 18px;font-size:clamp(34px,4.4vw,60px);color:var(--ink);overflow-wrap:anywhere;text-wrap:balance}
.display em{font-style:normal;color:var(--primary);background:linear-gradient(transparent 62%,var(--accent) 62%)}
.lede{font-size:18px;color:var(--muted);max-width:66ch;margin:0 0 24px}
.lede b{color:var(--ink);font-weight:600}
.btn{display:inline-flex;align-items:center;gap:8px;background:var(--primary);color:#fff;font-weight:600;padding:14px 28px;border-radius:4px;border:0;font-size:15px} .btn:hover{background:var(--primary-dark);text-decoration:none}
.btn.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--ink)} .btn.ghost:hover{background:var(--ink);color:#fff}
.steps{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 8px} .step{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)} .step b{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:var(--accent);font-weight:700} .step.cur b{background:var(--primary);color:#fff} .step.cur{color:var(--ink)}
section{padding-block:48px 8px} section.tight{padding-block:28px 8px}
h2.title{font-family:var(--mono);text-transform:uppercase;letter-spacing:-.03em;word-spacing:-.12em;font-weight:700;line-height:1;font-size:clamp(26px,3.2vw,40px);margin:0 0 10px} h2.title small{font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--primary);display:block;margin-bottom:10px;word-spacing:normal}
.sub{color:var(--muted);margin:0 0 22px;max-width:72ch} h3{font-size:18px;margin:26px 0 8px;font-weight:700}
.muted{color:var(--muted)} .mono{font-family:var(--mono)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:8px 0 8px}
.stat{padding:18px 18px 16px;border:1px solid var(--border);border-radius:12px;background:#fff} .stat.focal{background:var(--ink);color:#fff;border-color:var(--ink)}
.stat .k{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)} .stat.focal .k{color:var(--primary-glow)}
.stat .v{font-size:36px;font-weight:700;letter-spacing:-.02em;line-height:1.05;margin:8px 0 6px;font-variant-numeric:tabular-nums} .stat.focal .v{color:var(--accent)}
.stat .d{font-size:13px;color:var(--muted)} .stat.focal .d{color:#cfe3da}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fff;border:1px solid var(--border);border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top} tr:last-child td{border-bottom:0}
th{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600;background:var(--surface)}
td.n{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap} .tablewrap{overflow-x:auto;border-radius:12px}
.lvl{display:inline-block;font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.06em;padding:3px 9px;border-radius:999px;white-space:nowrap}
.lvl-rw,.lvl-read-ok{background:var(--primary-soft);color:var(--primary-deep)} .lvl-ro{background:var(--warn-soft);color:#7a4f00} .lvl-stalled,.lvl-read-stalled{background:#ffe8c2;color:#7a3e00} .lvl-down,.lvl-read-down{background:var(--danger-soft);color:#8a1f16} .lvl-na{background:var(--cream);color:var(--muted)}
code{font-family:var(--mono);font-size:12.5px;background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:1px 6px}
pre{font-family:var(--mono);font-size:12px;line-height:1.55;background:var(--ink);color:#e6f4ee;border-radius:10px;padding:14px 16px;overflow-x:auto;margin:0} pre code{background:none;border:0;color:inherit;padding:0}
pre .ev{color:var(--accent);font-weight:600} pre .ko{color:#ff8a7a} pre .okc{color:var(--primary-glow)}
.card{border:1px solid var(--border);border-radius:14px;background:#fff;padding:18px 20px} .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card h4{margin:0 0 6px;font-size:15px} .card .k{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary-deep);margin-bottom:8px;font-weight:600}
.notes{margin:0;padding-left:18px} .notes li{margin-bottom:8px;max-width:78ch} .notes li b{font-weight:600}
figure{margin:0} .figure{overflow-x:auto;padding-block:8px;background:#fff;border:1px solid var(--border);border-radius:14px} .figure svg{display:block;width:100%;min-width:720px;height:auto}
figcaption{font-size:13px;color:var(--muted);margin-top:10px;max-width:80ch}
.grid2{display:grid;grid-template-columns:1.15fr .85fr;gap:32px;align-items:start}
.matrix td:first-child{font-weight:600} .matrix .id{font-family:var(--mono);font-size:11px;color:var(--soft);display:block;font-weight:400}
.badge{display:inline-block;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary-deep);border:1px solid var(--primary);border-radius:3px;padding:1px 6px;font-weight:600}
.badge.y{color:#7a4f00;border-color:var(--accent);background:var(--accent-soft)}
.timeline{display:grid;grid-template-columns:76px 1fr;gap:6px 14px;font-size:13px;margin:8px 0} .timeline .t{font-family:var(--mono);color:var(--muted)} .timeline .e{border-left:2px solid var(--border);padding-left:12px} .timeline .e.ev{border-left-color:var(--accent);font-weight:600} .timeline .e.ko{border-left-color:var(--danger);color:#8a1f16} .timeline .e.ok{border-left-color:var(--primary)}
.req{margin:18px 0;border:1px solid var(--border);border-radius:12px;background:#fff} .req h4{margin:0;padding:12px 16px;font-size:15px;font-weight:600;border-bottom:1px solid var(--border);display:flex;gap:10px;align-items:center;background:var(--surface);border-radius:12px 12px 0 0} .req-body{padding:8px 16px 4px}
.scen{margin:10px 0 14px;border-left:3px solid var(--border);padding:6px 0 6px 14px} .scen-name{font-weight:600;margin-bottom:6px} .wt{display:grid;grid-template-columns:56px 1fr;gap:10px;margin:4px 0;font-size:14px} .kw{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--muted);padding-top:4px;font-weight:700} .kw.then{color:var(--primary-deep)}
.measured{margin-top:8px;padding:8px 12px;background:var(--note);border-left:3px solid var(--primary);border-radius:0 8px 8px 0;font-size:13px;font-family:var(--mono)} .measured div{margin:2px 0}
.delta{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin:20px 0 4px;color:var(--warn);font-weight:700} .delta-added{color:var(--primary-deep)}
.progress{height:10px;background:var(--cream);border:1px solid var(--border);border-radius:6px;overflow:hidden;margin:8px 0 4px} .bar{height:100%;background:var(--primary)}
.cb{display:inline-block;width:13px;height:13px;border:1.5px solid var(--soft);border-radius:3px;margin-right:8px;vertical-align:-2px} .cb.on{background:var(--primary);border-color:var(--primary)} .tid{font-family:var(--mono);font-size:12px;color:var(--muted);margin-right:6px}
.side{position:sticky;top:80px;align-self:start;font-size:13px;display:flex;flex-direction:column;gap:4px} .side a{color:var(--muted);padding:4px 8px;border-left:2px solid transparent} .side a:hover{color:var(--ink);border-left-color:var(--primary);text-decoration:none} .side .lbl{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--soft);margin:12px 0 2px}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px}
.doc p,.doc li{max-width:78ch} .doc table{display:block;overflow-x:auto}
.eyebrow-sm{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--soft);margin:12px 0 0}
footer{margin-top:64px;background:var(--footer);color:#cfe3da;padding-block:28px} footer .container{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-family:var(--mono);font-size:11px} footer a{color:var(--primary-glow)}
@media (max-width:900px){.stats{grid-template-columns:1fr 1fr} .grid2{grid-template-columns:1fr} .layout{grid-template-columns:1fr} .side{position:static;flex-direction:row;flex-wrap:wrap} .side .lbl{width:100%}}
@media (max-width:520px){.stats{grid-template-columns:1fr}}
"""

def shell(title, description, body, current, extra_head=""):
    """Full page: sticky nav with the three demo steps, body, footer."""
    nav = [("index.html", "01 精簡報告", "index"), ("specs.html", "02 實驗設計", "specs"), ("results.html", "03 過程與結果", "results"), ("howto.html", "部署與操作", "howto"), ("deck/", "投影片 ↗", "deck"), ("explore.html", "互動架構圖 ↗", "explore")]
    links = "".join(f'<a href="{h}" class="{"cur" if k == current else ""}">{t}</a>' for h, t, k in nav)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{FONTS}
<style>{CSS}</style>{extra_head}
</head>
<body>
<header class="top"><div class="container"><a class="brand" href="index.html"><i></i> Apache Doris · HA POC</a><nav class="links">{links}</nav></div></header>
{body}
<footer><div class="container"><span>Apache Doris 4.1.1 · GCP asia-east1 a/b/c · Terraform + Ansible + demo.sh</span><span>產生於 {datetime.date.today().isoformat()} · 視覺依 doris.apache.org 配色</span></div></footer>
</body>
</html>
"""

def steps(current):
    names = [("index", "精簡報告"), ("specs", "實驗設計"), ("results", "過程與結果")]
    return '<div class="steps">' + "".join(f'<span class="step {"cur" if k == current else ""}"><b>{i+1}</b>{n}</span>' for i, (k, n) in enumerate(names)) + "</div>"

def lvl(level, zh=None):
    z = zh or {"rw": "讀寫正常", "ro": "只讀", "down": "不可用", "stalled": "卡住", "read-ok": "讀取正常", "read-down": "讀取失敗", "read-stalled": "讀取卡住"}.get(level, "n/a")
    return f'<span class="lvl lvl-{level if level else "na"}">{z}</span>'
