---
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

<div class="abs-br m-6 text-sm op70">2026-09-16 · 線上版：https://doris-ha-demo-195642473078.asia-east1.run.app</div>

<!--
開場：一句話講清楚實驗回答的問題。三頁網站的順序是 精簡報告 → 實驗設計 → 過程與結果，這份投影片照同樣順序。
-->

---
layout: two-cols
---

# 架構：一個叢集、兩層各自 HA

- 3 台 VM（zone a/b/c），每台 1 個 **FE** + 1 個 **BE**
- 3 個 FE 角色都是 FOLLOWER（有投票權），以 **quorum** 選出 1 個 master；任一 FE 都能接連線，寫入轉發給 master
- 3 個 BE 是一個資料池，每份資料 **3 個 replica** 各放一個 zone，寫入要 2/3 成功
- client 帶三台 FE 的**主機清單**，不經 LB；第一台連不上就試下一台
- FE + BE 同機只是 POC 省錢

::right::

<img src="/arch-normal.svg" class="mt-4 rounded border" />

<!--
強調兩件事：FE 層靠 quorum（3 台活 2 台），BE 層靠 replica quorum（2/3）。這兩個數字決定了後面所有結果。
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
| 方式 | crash（kill -9，systemd 10 秒重啟）/ dead（systemctl stop）/ hang（kill -STOP）/ stop（VM 停機） |
| 位置 | master 所在 / follower 所在 |

**雙重故障**：VM 停 + FE dead、VM 停 + BE dead、兩台 VM、交錯

::right::

**結果等級（3 輪最差）**

- <span class="lvl rw">讀寫正常</span> 中斷後全部恢復
- <span class="lvl ro">只讀</span> 寫入持續失敗、SELECT 正常
- <span class="lvl down">不可用</span> 查詢也失敗
- <span class="lvl st">卡住</span> 沒報錯也沒回應

**量測**：中斷秒數 = 失敗時間 + 無回應時間（間隔 > 5 秒）；等級看故障中最後 30 秒

<div class="mt-4 text-sm op70">設計用 OpenSpec 寫：每格一個 Scenario（WHEN / THEN 預期）；實測數字另存 results/，不寫進 spec。</div>

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
| 設定 | **Ansible** `ansible/` | JDK、Doris、conf、systemd、FE/BE 註冊、三個 probe |
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

<div class="text-sm op70 mt-2">break 可疊加（雙重故障），restore 依相反順序全部還原；crash 由 systemd 自動重啟。<code>.state/faults</code> 記錄目前的故障，<code>demo.sh status</code> 隨時可看。</div>

---

# 狀態機：叢集可用性

<img src="/avail-state.svg" class="rounded border" style="max-height:360px;margin:auto" />

<div class="text-sm op70 mt-2">FE ≥ 2 且 BE ≥ 2 才讀寫正常；BE = 1 只讀；FE = 1 不可用；master FE 被暫停但 TCP 還在 → 卡住，直到重新選主或恢復。</div>

---

# 指令：從零到一輪實驗

```bash
./demo.sh plan            # terraform plan + ansible --check --diff
./demo.sh up              # 建 4 VM → 裝 Doris → 組叢集 → 三個 probe → 灌 1 萬筆（約 10 分鐘）

./demo.sh monitor         # 終端 1：三個 client 即時捲動
./demo.sh break --target fe --mode hang --on master     # 終端 2：製造故障
./demo.sh restore         # 還原全部故障、等健康
./demo.sh measure         # 失敗時間、無回應時間、可用性等級

./venv/bin/python experiments/run_matrix.py --pass 1    # 整個矩陣：開機 → 16 格 → 關機
./experiments/finalize.sh # 回填 spec → 產網站 → 部署
./demo.sh stop            # 關機省錢；down = terraform destroy
```

<div class="text-sm op70 mt-2">任何指令加 <code>--dry-run</code> 只印出會執行的 gcloud / terraform / ansible 指令。</div>

---

# 結果：單一故障（12 格 × 3 輪）

| 故障 | mysql | jdbc | arrow-flight | 結論 |
|---|---|---|---|---|
| 三個 client 同時觀察 VM 停機 | 讀寫正常 26～29s | 讀寫正常 20～33s | 讀取正常 29～36s | **讀寫正常** |
| master 所在 VM 停機，client 直連 master | 讀寫正常 0～32s | 讀寫正常 1～33s | 讀取正常 0～29s | **讀寫正常** |
| master 所在 VM 停機，client 連在 follower | 讀寫正常 2～35s | 讀寫正常 1～33s | 讀取正常 1～30s | **讀寫正常** |
| follower 所在 VM 停機 | 讀寫正常 0～13s | 讀寫正常 0～15s | 讀取正常 2～19s | **讀寫正常** |
| master FE crash | 讀寫正常 6～25s | 讀寫正常 9～29s | 讀取正常 6～7s | **讀寫正常** |
| follower FE crash | 讀寫正常 1～4s | 讀寫正常 0～2s | 讀取正常 3～5s | **讀寫正常** |
| master FE dead | 讀寫正常 0～25s | 讀寫正常 1～24s | 讀取正常 0～9s | **讀寫正常** |
| master FE hang | 只讀 73～137s | 卡住 83～139s | 讀取正常 72～136s | **卡住** |
| follower FE hang | 讀寫正常 18～26s | 讀寫正常 45～54s | 讀取正常 38～40s | **讀寫正常** |
| BE crash | 讀寫正常 0～23s | 讀寫正常 0～18s | 讀取正常 0～2s | **讀寫正常** |
| BE dead | 讀寫正常 0s | 讀寫正常 0～3s | 讀取正常 1s | **讀寫正常** |
| BE hang | 讀寫正常 28～36s | 讀寫正常 27～37s | 讀取正常 28～37s | **讀寫正常** |

<!--
重點：除了 master FE hang，全部讀寫正常，最慢 54 秒恢復；秒數是 3 輪範圍。
-->

---

# 結果：雙重故障（4 格 × 3 輪）

| 故障 | mysql | jdbc | arrow-flight | 結論 |
|---|---|---|---|---|
| VM 停 + 另一台 FE dead | 不可用 106～130s | 不可用 108～132s | 讀取失敗 107～134s | **不可用** |
| VM 停 + 另一台 BE dead | 只讀 17～26s | 只讀 19～25s | 讀取正常 32～36s | **只讀** |
| 兩台 VM 停 | 不可用 130～131s | 不可用 130～131s | 讀取卡住 131～132s | **不可用** |
| 交錯故障 | 只讀 84～102s | 不可用 146～149s | 讀取失敗 172～177s | **不可用** |

<div class="mt-4">FE 剩 1/3 → <span class="lvl down">不可用</span>（連查詢都失敗）；BE 剩 1/3 → <span class="lvl ro">只讀</span>；兩層都 1/3 → <span class="lvl down">不可用</span>。規則：FE 和 BE 各自要 3 台活 2 台（quorum）才能寫。</div>

---
layout: two-cols
---

# 三個值得記住的發現

1. **master FE hang：偵測慢又不穩定**：3 輪裡 2 輪在 120 秒觀察期內沒選出新 master、1 輪 73 秒後選主。FE 被凍結但 TCP port 還開著，其他 FE 一開始不覺得它掛了；client 只能讀或整個卡住 → 等級「卡住」。
2. **FE 剩 1/3 連查詢都不行**：VM 停 + FE dead 3 輪 mysql / jdbc / arrow-flight 全部失敗。交錯故障時僅存的 follower FE 還能回 mysql 的 SELECT（只讀），jdbc 不可用，不能依賴。
3. **client 先連 master 或 follower 差不多**：mysql 先連 master 0～32s、先連 follower 2～35s。差別只在有沒有碰到 VM 關機期間等 timeout。

::right::

<img src="/timeline.svg" class="mt-2 rounded border" />

<div class="text-xs op70 mt-1">一次故障的時間軸（停 master VM，第 1 輪，mysql client）</div>

---

# 資料一致性與恢復

<div class="grid grid-cols-3 gap-6 mt-8 text-center">
<div class="card"><div class="big">0</div>筆資料錯誤<br><span class="op70">48 次執行 · 26,438 次操作，每次 SELECT 驗證</span></div>
<div class="card"><div class="big">12 / 12</div>replica 正常<br><span class="op70">每次 restore 後 4～266 秒回到 3 FE / 3 BE</span></div>
<div class="card"><div class="big">0</div>人工介入<br><span class="op70">VM 開回來 systemd 自動起 FE/BE、自動回到叢集</span></div>
</div>

<div class="mt-8 op80">寫入失敗就換一把新 key 重新開始，不會留下寫一半的資料；雙重故障恢復時，第二個元件回來的那一刻就恢復可寫。</div>

---

# 建議

- **client 端**：JDBC 多主機連線字串 `jdbc:mysql://fe1,fe2,fe3/db` 最省事；自行實作時 timeout 2～3 秒、失敗重連時**換下一台 FE**；hang 時連線不會 reset，timeout 別設太長
- **架構**：正式環境 FE / BE 分開機器；FE 3 台是最低要求，掛 1 台就沒有備援
- **監控**：把 <code>SHOW FRONTENDS</code> 的 master 存在與 hang 偵測（例如 9030 timeout）接進告警，master hang 是唯一「沒報錯但不能用」的情境
- **寫入通道**：Arrow Flight SQL 在 4.1.1 只走查詢；寫入用 MySQL 協定或 Stream Load
- **下一步**：網路分割、zone 故障、調 <code>bdbje_heartbeat_timeout_second</code> 看 hang 偵測能不能縮短

---
layout: iframe
url: https://doris-ha-demo-195642473078.asia-east1.run.app/results.html
---

---
layout: center
class: text-center
---

# 線上版

精簡報告 · 實驗設計（OpenSpec）· 過程與全部結果 · 部署與操作 · 互動架構圖

**https://doris-ha-demo-195642473078.asia-east1.run.app**

<div class="mt-6 op70 text-sm">結果、log、spec、Terraform / Ansible、probe（測試程式）都在同一個 repo；<code>experiments/finalize.sh</code> 一鍵重產這些頁面。</div>
