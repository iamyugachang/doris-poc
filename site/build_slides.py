#!/usr/bin/env python3
"""Generate slides/slides.md (Slidev deck, zh-TW) from results/summary.json + the exported diagrams.
Run: ./venv/bin/python site/build_slides.py ; then: cd slides && npx slidev build slides.md --base /slides/"""
import json, pathlib, shutil, re, datetime
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://doris-ha-demo-195642473078.asia-east1.run.app"
agg = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
order = [s["id"] for s in yaml.safe_load((ROOT / "experiments/scenarios.yaml").read_text(encoding="utf-8"))["scenarios"]]
ids = [i for i in order if i in agg]
pub = ROOT / "slides/public"; pub.mkdir(parents=True, exist_ok=True)
for f in (ROOT / "site/diagrams").glob("*.svg"):
    txt = f.read_text(encoding="utf-8")
    # the architecture SVGs use CSS vars from the site theme: inline them for standalone use
    for k, v in {"--paper": "#fff", "--ink": "#0f1a14", "--muted": "#4f5e56", "--soft": "#7f8f86", "--rule": "#d9eee8", "--rule-solid": "#d9eee8", "--accent": "#11a679", "--accent-tint": "rgba(17,166,121,.10)", "--white": "#fff", "--ink-05": "rgba(15,26,20,.05)", "--ink-02": "rgba(15,26,20,.02)", "--ink-20": "rgba(15,26,20,.20)", "--ink-30": "rgba(15,26,20,.30)", "--muted-10": "rgba(79,94,86,.10)", "--muted-15": "rgba(79,94,86,.15)", "--link": "#0b7a58", "--sans": "Inter,Noto Sans TC,sans-serif", "--mono": "JetBrains Mono,monospace"}.items():
        txt = txt.replace(f"var({k})", v)
    (pub / f.name).write_text(txt, encoding="utf-8")

ZH = {"rw": "讀寫正常", "ro": "只讀", "down": "不可用", "stalled": "卡住", "read-ok": "讀取正常", "read-down": "讀取失敗", "read-stalled": "讀取卡住", "n/a": "n/a"}
def rng(a, c):
    x, y = a["clients"][c]["impact_min"], a["clients"][c]["impact_max"]
    return "—" if x is None else (f"{x}s" if x == y else f"{x}～{y}s")
def row(i):
    a = agg[i]; name = a["scenario"].split("（")[0]
    return f'| {name} | {ZH[a["clients"]["mysql"]["worst"]]} {rng(a,"mysql")} | {ZH[a["clients"]["jdbc"]["worst"]]} {rng(a,"jdbc")} | {ZH[a["clients"]["flight"]["worst"]]} {rng(a,"flight")} | **{ZH[a["overall"]]}** |'
single = [i for i in ids if not i.startswith("double-")]; double = [i for i in ids if i.startswith("double-")]
n_runs = sum(len(agg[i]["passes"]) for i in ids)
verify_fail = sum(f.read_text(encoding="utf-8", errors="replace").count("verify id=") for f in ROOT.glob("results/pass-[1-9]/*/*.log"))
today = datetime.date.today().isoformat()

deck = f'''---
theme: default
title: Apache Doris 三節點 HA 故障矩陣實驗
titleTemplate: '%s'
info: |
  Doris 4.1.1 on GCP asia-east1 a/b/c — FE / BE / VM 的 crash、dead、hang、stop 與雙重故障下，三種 client 的可用性
author: doris-poc
lang: zh-TW
fonts:
  sans: Inter, Noto Sans TC
  mono: JetBrains Mono
colorSchema: light
transition: fade
mdc: true
---

# FE 掛了、BE 掛了、整台 VM 掛了 <br> <span class="g">client 還能寫嗎？</span>

Apache Doris 4.1.1 · GCP asia-east1 三個 zone · 16 種故障 × 3 輪 · 三種協定 client

<div class="abs-br m-6 text-sm op70">{today} · 線上版：{SITE}</div>

<!--
開場：一句話講清楚實驗回答的問題。三頁網站的順序是 精簡報告 → 實驗設計 → 過程與結果，這份投影片照同樣順序。
-->

---
layout: two-cols
---

# 架構：一個叢集、兩層各自 HA

- 3 台 VM（zone a/b/c），每台 1 個 **FE** + 1 個 **BE**
- FE 三個都是 FOLLOWER，**多數決**選 1 個 master；任一 FE 都能接連線，寫入轉發給 master
- BE 是一個資料池，每個 tablet **三副本**各放一個 zone，寫入要 2/3 成功
- client 帶三台 FE 的**主機清單**，不經 LB；第一台連不上就試下一台
- FE + BE 同機只是 POC 省錢

::right::

<img src="/arch-normal.svg" class="mt-4 rounded border" />

<!--
強調兩件事：FE 層靠 quorum（2/3），BE 層靠副本 quorum（2/3）。這兩個數字決定了後面所有結果。
-->

---

# 三個 client、同一套循環

<div class="grid grid-cols-3 gap-4 mt-6">
<div class="card"><b>mysql</b><br>Python + pymysql，FE :9030<br><span class="op70">自己依主機清單 failover</span></div>
<div class="card"><b>jdbc</b><br>Java + Connector/J 多主機 URL<br><span class="op70">driver 內建 failover</span></div>
<div class="card"><b>arrow-flight</b><br>Python + ADBC Flight SQL，FE :8070<br><span class="op70">Doris 4.1.1 只支援查詢 → SELECT-only</span></div>
</div>

<div class="mt-8 text-center text-xl">
<code>INSERT(ver=1)</code> → <code>UPSERT(ver=2)</code> → <code>SELECT 驗 ver=2</code> → <code>DELETE</code> → <code>SELECT 驗不存在</code>
</div>

<div class="mt-4 op80">每秒一步、每輪換一把 key、UNIQUE KEY（merge-on-write）表。寫入失敗後另開連線做 <b>讀取檢查</b>，才能分辨「只讀」和「不可用」。</div>

<!--
UNIQUE KEY 表讓同 key 的 INSERT 就是 UPSERT。讀取檢查是第 2 輪起加的，第 1 輪靠 flight 的讀取結果推斷。
-->

---
layout: two-cols
---

# 實驗設計：故障矩陣

**對象 × 方式 × 位置**

| 維度 | 值 |
|---|---|
| 對象 | FE 程序 / BE 程序 / 整台 VM |
| 方式 | crash（kill -9，systemd 10 秒拉起）/ dead（systemctl stop）/ hang（kill -STOP）/ stop（VM 停機） |
| 位置 | master 所在 / follower 所在 |

**雙重故障**：VM 停 + FE dead、VM 停 + BE dead、兩台 VM、交錯

::right::

**可用性等級（三輪最差）**

- <span class="lvl rw">讀寫正常</span> 中斷後全部恢復
- <span class="lvl ro">只讀</span> 寫入持續失敗、SELECT 正常
- <span class="lvl down">不可用</span> 查詢也失敗
- <span class="lvl st">卡住</span> 沒報錯也沒回應

**量測**：受影響秒數 = 失敗視窗 ∪ 卡頓（間隔 > 5s）；等級看故障中最後 30 秒

<div class="mt-4 text-sm op70">規格用 OpenSpec 寫：每格一個 Scenario（WHEN / THEN 預期），跑完由工具回填三輪實測。</div>

<!--
先講設計再講結果。等級的判定規則要講清楚，尤其「卡住」是為了 master hang 才加的。
-->

---
layout: two-cols
---

# 工具分工

| 層 | 工具 | 負責 |
|---|---|---|
| 資源 | **Terraform** `infra/` | 4 台 VM、防火牆、API、開關機（`vm_status`）、產生 inventory |
| 設定 | **Ansible** `ansible/` | JDK、Doris、conf、systemd、FE/BE 註冊、三個探測 |
| 動作 | **demo.sh** | monitor / break / restore / measure；up / stop / start / down 薄包裝 |

- 狀態交給宣告式工具，動作留在 shell
- `up` = terraform apply → ansible-playbook → 灌資料，可重跑
- `stop` / `start` = 換 `vm_status` 再 apply

::right::

<img src="/flow.svg" class="mt-2 rounded border" />

<!--
Terraform 只管 GCP 上「存在什麼」，Ansible 管機器裡「長什麼樣」，兩者都可重跑；一次性的動作才是腳本。
-->

---

# 狀態機：環境

<img src="/env-state.svg" class="rounded border" style="max-height:380px;margin:auto" />

<div class="text-sm op70 mt-2">break 可疊加（雙重故障），restore 依相反順序全部逆轉；crash 由 systemd 自動拉起。<code>.state/faults</code> 記錄目前的故障，<code>demo.sh status</code> 隨時可看。</div>

---

# 狀態機：叢集可用性

<img src="/avail-state.svg" class="rounded border" style="max-height:360px;margin:auto" />

<div class="text-sm op70 mt-2">FE ≥ 2 且 BE ≥ 2 才讀寫正常；BE = 1 只讀；FE = 1 不可用；master FE 被暫停但 TCP 還在 → 卡住，直到重新選主或恢復。</div>

---

# 指令：從零到一輪實驗

```bash
./demo.sh plan            # terraform plan + ansible --check --diff
./demo.sh up              # 建 4 VM → 裝 Doris → 組叢集 → 三個探測 → 灌 1 萬筆（約 10 分鐘）

./demo.sh monitor         # 終端 1：三個 client 即時捲動
./demo.sh break --target fe --mode hang --on master     # 終端 2：注入故障
./demo.sh restore         # 逆轉全部故障、等健康
./demo.sh measure         # 失敗視窗、卡頓、可用性等級

./venv/bin/python experiments/run_matrix.py --pass 1    # 整個矩陣：開機 → 16 格 → 關機
./experiments/finalize.sh # 回填 spec → 產網站 → 部署
./demo.sh stop            # 關機省錢；down = terraform destroy
```

<div class="text-sm op70 mt-2">任何指令加 <code>--dry-run</code> 只印出會執行的 gcloud / terraform / ansible 指令。</div>

---

# 結果：單一故障（{len(single)} 格 × 3 輪）

| 故障 | mysql | jdbc | arrow-flight | 結論 |
|---|---|---|---|---|
{chr(10).join(row(i) for i in single)}

<!--
重點：除了 master FE hang，全部讀寫正常；秒數是三輪範圍，差異來自 client 是否卡在轉發給快消失的 master。
-->

---

# 結果：雙重故障（{len(double)} 格 × 3 輪）

| 故障 | mysql | jdbc | arrow-flight | 結論 |
|---|---|---|---|---|
{chr(10).join(row(i) for i in double)}

<div class="mt-4">FE 剩 1/3 → <span class="lvl down">不可用</span>（連查詢都拿不到 metadata）；BE 剩 1/3 → <span class="lvl ro">只讀</span>；兩層都 1/3 → 看僅存 FE 是否 master。</div>

---
layout: two-cols
---

# 三個值得記住的發現

1. **master FE hang（SIGSTOP）**：第 1 輪 2 分鐘沒選主、第 2/3 輪 63 秒後選主。期間 jdbc 一筆卡住到恢復、mysql 每筆 8 秒逾時、flight 每筆 9 秒 → 等級「卡住」。BDB JE 心跳只看 TCP 是否存活。
2. **FE 剩 1/3 連讀都不行**：僅存的是 follower 就拒絕連線；是 master 就全部逾時。
3. **中斷長短不看連 master 或 follower**，看 client 有沒有卡在「VM 正在關機那 25 秒」裡的轉發逾時：碰到 20～40 秒，沒碰到 0～2 秒。

::right::

<img src="/timeline.svg" class="mt-2 rounded border" />

<div class="text-xs op70 mt-1">一次故障的時間軸（停 master VM，第 1 輪，mysql client）</div>

---

# 資料一致性與恢復

<div class="grid grid-cols-3 gap-6 mt-8 text-center">
<div class="card"><div class="big">{verify_fail}</div>筆資料不一致<br><span class="op70">{n_runs} 次執行的 SELECT 驗證</span></div>
<div class="card"><div class="big">12 / 12</div>副本 OK<br><span class="op70">每次 restore 後都回到 3 FE / 3 BE</span></div>
<div class="card"><div class="big">0</div>人工介入<br><span class="op70">VM 開回來 systemd 自動起 FE/BE、自動歸隊</span></div>
</div>

<div class="mt-8 op80">寫入在中斷視窗內失敗會換新 key 重來，不留下半套資料；雙重故障恢復時，第二個元件回來的那一刻就恢復可寫。</div>

---

# 建議

- **client 端**：JDBC 多主機 URL 最省事；自行實作時逾時 2～3 秒、失敗重連時**輪替主機**，別回到同一台 follower
- **架構**：正式環境 FE / BE 分開機器；FE 3 台是最低要求，掛 1 台就沒有冗餘
- **監控**：把 <code>SHOW FRONTENDS</code> 的 master 存在與 hang 偵測（例如 9030 逾時）接進告警，master hang 是唯一「沒報錯但不能用」的情境
- **寫入通道**：Arrow Flight SQL 在 4.1.1 只走查詢；寫入用 MySQL 協定或 Stream Load
- **下一步**：網路分割、zone 故障、調 <code>bdbje_heartbeat_timeout_second</code> 看 hang 偵測能不能縮短

---
layout: iframe
url: {SITE}/results.html
---

---
layout: center
class: text-center
---

# 線上版

精簡報告 · 實驗設計（OpenSpec）· 過程與全部結果 · 部署與操作 · 互動架構圖

**{SITE}**

<div class="mt-6 op70 text-sm">結果、log、spec、Terraform / Ansible、探測程式都在同一個 repo；<code>experiments/finalize.sh</code> 一鍵重產這些頁面。</div>
'''
(ROOT / "slides/slides.md").write_text(deck, encoding="utf-8")
(ROOT / "slides/style.css").write_text('''
:root { --slidev-theme-primary: #11a679; }
.slidev-layout { font-family: Inter, "Noto Sans TC", sans-serif; background: #fffcf5; color: #0f1a14; }
.slidev-layout h1 { font-family: "JetBrains Mono", monospace; text-transform: uppercase; letter-spacing: -.03em; font-weight: 700; color: #0f1a14; }
.slidev-layout h1 .g { color: #11a679; }
.slidev-layout a { color: #0b7a58; }
.slidev-layout code { color: #0b7a58; background: #f4fbf8; }
.slidev-layout table { font-size: .78rem; }
.slidev-layout th { font-family: "JetBrains Mono", monospace; font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; color: #4f5e56; background: #f4fbf8; }
.card { border: 1px solid #d9eee8; border-radius: 12px; padding: 14px 16px; background: #fff; }
.card .big { font-size: 2.6rem; font-weight: 700; color: #11a679; line-height: 1.1; }
.lvl { display: inline-block; font-family: "JetBrains Mono", monospace; font-size: .7rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.lvl.rw { background: #c9ffe6; color: #0b7a58; } .lvl.ro { background: #fff1c2; color: #7a4f00; } .lvl.down { background: #ffe2dd; color: #8a1f16; } .lvl.st { background: #ffe8c2; color: #7a3e00; }
''', encoding="utf-8")
print(f"wrote slides/slides.md ({len(deck):,} chars), public/ diagrams: {len(list(pub.glob('*.svg')))}")
