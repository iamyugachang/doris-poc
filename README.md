# doris-poc — Apache Doris HA 故障矩陣實驗（GCP）

驗證 Apache Doris 4.1.1 在 GCP 單一 region 三個 zone、每台 VM 各跑一個 FE + 一個 BE 的部署下，**FE / BE / 整台 VM 發生 crash、dead、hang、stop 以及雙重故障時，三種協定的 client（mysql、jdbc、arrow-flight）還能不能讀寫、中斷多久、資料有沒有不一致**。

- 線上 demo（三頁對應 demo 順序）：https://doris-ha-demo-195642473078.asia-east1.run.app
  - `/` 精簡報告（矩陣 + 結論）→ `/specs.html` 實驗設計（OpenSpec）→ `/results.html` 過程與全部結果 → `/howto.html` 部署與操作（Terraform / Ansible 分工、狀態機、指令）→ `/deck/` 投影片（open-slide，React）→ `/slides/` 投影片（Slidev）→ `/explore.html` 互動架構圖
- 規格：`openspec/`（主 spec = 環境契約 + 故障情境；change `fault-matrix` 已 archive 至 `openspec/changes/archive/`。spec 只有實驗內容與假設，實測在 results/ 與 results.html）
- 結果：`results/pass-{1,2,3}/<情境>/`（三份 client log + summary.json），彙整 `results/summary.json`

```
Client VM（同 VPC）三個探測同時跑，每秒一步 INSERT→UPSERT→SELECT→DELETE→SELECT，寫入失敗後另開連線做讀取檢查
  mysql  Python + pymysql :9030（自己依 host 清單 failover）
  jdbc   Java + Connector/J 多主機 URL :9030（driver failover）
  flight Python + ADBC Arrow Flight SQL :8070（Doris 4.1.1 只支援查詢 → SELECT-only）
   └─> doris-1 / doris-2 / doris-3（asia-east1-a/b/c）各 1 FE FOLLOWER + 1 BE，表 replication_num=3
```

## 分工：Terraform、Ansible、demo.sh

| 層 | 工具 | 負責什麼 | 不負責什麼 |
|---|---|---|---|
| 資源 | **Terraform**（`infra/`） | GCP 上「存在什麼」：4 台 VM（3 Doris + 1 client）、防火牆、API 啟用、VM 開關機狀態、產生 Ansible inventory | 機器裡面的軟體與設定、Doris 叢集成員 |
| 設定 | **Ansible**（`ansible/`） | 機器裡「長什麼樣」：JDK、Doris 安裝與 conf、systemd unit、FE/BE 註冊成叢集、client VM 的三個探測 | 開關機、故障注入、量測 |
| 動作 | **demo.sh** + `experiments/` | 「做一件事」：monitor / break / restore / measure，以及 up / stop / start / down 的薄包裝；矩陣執行器、結果彙整、網站產生 | 描述狀態（那是前兩層的事） |

### Terraform（`infra/`）

- `main.tf`：`google_compute_instance.doris[3]`、`google_compute_instance.client`、`google_compute_firewall.operator`（9030/8030/8040 只放行操作者 IP）、`google_project_service`（compute / run / cloudbuild / artifactregistry，destroy 時不關閉）、選用的 Cloud Run 服務（`site_image` 變數）
- `variables.tf`：專案、region、zone 清單、機型、磁碟、`vm_status`（RUNNING / TERMINATED）、`allow_ip`、`ssh_user` / `ssh_public_key_file`
- `inventory.tftpl` → 每次 apply 產生 `ansible/inventory.ini`（主機名、內外網 IP、zone、哪台是 FE seed）
- `tf.sh`：包裝 `terraform`，用目前 gcloud 使用者的 access token 認證（不需 application-default login），自動帶 `allow_ip`（目前對外 IP）與 `ssh_user`
- 開關機 = `terraform apply -var vm_status=…`，只針對 instance 資源；隨後一次完整 apply 更新 inventory（開機後外部 IP 會變）
- `plan` / `destroy` 就是 `./demo.sh plan` / `./demo.sh down`

### Ansible（`ansible/`）

- `site.yml` 三個 play，依序：
  1. `doris_node`（hosts: doris）— apt JDK 17 + mysql client、sysctl / limits / THP、下載解壓 Doris（已存在則跳過）、`blockinfile` 寫 fe.conf / be.conf、FE heap、`fe.env`（follower 帶 `--helper seed:9010`）、systemd unit `doris-fe` / `doris-be`（enable；handler 只在服務已在跑時 restart）
  2. `doris_cluster`（hosts: doris，動作在 `fe_seed=true` 那台）— 起 seed FE、等 9030；舊叢集沒 quorum 就先起全部 FE；`ALTER SYSTEM ADD FOLLOWER / BACKEND`（已存在忽略）；全部 FE/BE start
  3. `probe_client`（hosts: client）— 時區、JDK、venv（pymysql / pyarrow / adbc）、Connector/J、javac、三個 systemd unit `probe-{mysql,jdbc,flight}`（不 enable，由 `monitor` 啟動；程式碼變更時自動 restart）
- `group_vars/all.yml`：Doris 版本與下載網址、路徑、`priority_networks`、FE heap、BE mem_limit、探測指令
- 可重跑：第二次執行 `changed=0`；`--check --diff` 可預演；`--limit client` 只重佈探測
- 執行時 stdio 需為阻塞（`< /dev/null 2>&1 | cat`），`demo.sh` 已處理

### demo.sh 與 experiments/

| 指令 | 做什麼 |
|---|---|
| `./demo.sh up` | terraform apply（開機 + inventory）→ ansible-playbook site.yml → 建表灌 1 萬筆。可重跑 |
| `./demo.sh plan` | terraform plan + ansible --check --diff |
| `./demo.sh status` | FE / BE 存活數、master、副本狀態、目前注入中的故障 |
| `./demo.sh monitor [--fresh] [--order master-first\|follower-first]` | 在 client VM 起三個探測並合併即時捲動 |
| `./demo.sh break [--target fe\|be\|vm] [--mode crash\|dead\|hang\|stop] [--on master\|follower\|<vm>]` | 注入故障（預設停 master 所在 VM）；可連續執行疊加 |
| `./demo.sh restore` | 逆序逆轉全部故障（VM start / systemctl start / kill -CONT），等叢集健康 |
| `./demo.sh measure [--json] [--label X]` | 拉回三份 log：失敗視窗、卡頓、可用性等級（讀寫正常 / 只讀 / 不可用 / 卡住） |
| `./demo.sh stop` / `start` | terraform vm_status 切換；start 後自動歸隊、確保測試表 |
| `./demo.sh client` | 只跑 probe_client role |
| `./demo.sh down` | terraform destroy（VM + 防火牆；API 與 Cloud Run 保留） |
| `experiments/run_matrix.py --pass N [--only id,…]` | 一輪 = 開機 → 逐格（`experiments/scenarios.yaml`）monitor → baseline → break → 觀察 → measure → restore → measure → 關機 |
| `experiments/fill_results.py` | 從 log 重算三輪結果 → `results/summary.json`（results.html 與 index.html 的資料來源；不寫進 spec） |
| `experiments/finalize.sh` | 彙整 → 產四頁（`site/build_*.py`）→ `openspec validate` → 部署 Cloud Run |
| `site/build_slides.py` → `cd slides && npx slidev build slides.md --base /slides/ --out ../site/slides` | 由同一份結果產生 Slidev 投影片（線上 `/slides/`；本機 `npx slidev slides.md` 可編輯預覽） |
| `cd openslide && pnpm build --out-dir ../site/deck` | open-slide 投影片（`openslide/slides/doris-ha/index.tsx`，React 手寫 14 頁；線上 `/deck/`；本機 `pnpm dev` 有簡報者模式與講稿） |
| 任何 demo.sh 指令 + `--dry-run` | 只印出會執行的 gcloud / terraform / ansible 指令 |

## 快速開始

```bash
# 前置：gcloud 已登入且對專案有 Compute 權限；terraform ≥ 1.6 在 PATH；python3
./demo.sh up                 # 約 10 分鐘（含 3.4 GB Doris 下載）
./demo.sh monitor            # 另開終端看三個 client 即時讀寫
./demo.sh break --target fe --mode hang --on master
./demo.sh restore
./demo.sh measure
./demo.sh stop               # 省錢；或 ./demo.sh down 全刪
```

## 故障矩陣結果（2026-09-15，16 格 × 3 輪 = 48 次執行）

| 故障（三輪最差等級） | mysql | jdbc | arrow-flight |
|---|---|---|---|
| 停 master VM／停 follower VM | 讀寫正常 0～35s | 讀寫正常 0～33s | 讀取正常 0～36s |
| master FE crash / dead | 讀寫正常 0～25s | 讀寫正常 1～29s | 讀取正常 0～9s |
| follower FE crash | 讀寫正常 1～4s | 0～2s | 3～5s |
| master FE hang（SIGSTOP） | **卡住**：兩輪 120s 內不選主、一輪 73s 後選主 | 卡住 83～139s | 讀取正常 72～136s |
| follower FE hang | 讀寫正常 18～26s | 45～54s | 38～40s |
| BE crash / dead / hang | 讀寫正常 0～36s | 0～37s | 0～37s |
| VM 停 + 另一台 FE dead（FE 1/3） | **不可用** | 不可用 | 讀取失敗 |
| VM 停 + 另一台 BE dead（BE 1/3） | **只讀** | 只讀 | 讀取正常 |
| 兩台 VM 停 | 不可用 | 不可用 | 讀取卡住 |
| 交錯（VM 停 + BE dead + FE dead） | 只讀（僅存 FE 是 master） | 不可用 | 讀取失敗 |

48 次執行 0 筆資料不一致；每次 restore 後都回到 3 FE / 3 BE、12 副本 OK。中斷秒數 = 失敗視窗（第一次失敗到下一次成功）與卡頓（連續操作間隔 > 5 秒）的聯集，含 client 自己的逾時（connect 3s、read/write 8s）。本次 asia-east1-c 缺 e2-standard-4，doris-3 以 n2 / n2d-standard-4 執行（見 `results/run-notes.md`）；上一次（2026-09-11）結果在 `results/archive/`。

## 目錄

```
infra/          Terraform（資源）            ansible/        Ansible roles（設定）
demo.sh         動作指令                     cluster.py      本機端狀態 / 量測 / 分析
clients/        三個探測程式（部署到 client VM） experiments/    scenarios.yaml、run_matrix.py、fill_results.py、finalize.sh
openspec/       規格（主 spec + change）      results/        三輪原始結果與彙整
site/           三頁網站產生器與輸出           deploy/         Cloud Run 靜態站（nginx）
slides/         Slidev 投影片                 openslide/      open-slide 投影片（React）
logs/           矩陣之前的手動實測紀錄
```

## 成本（asia-east1）

- 運行中約 US$0.51/hr（3 × e2-standard-4 + e2-small + 170 GB pd-balanced）；一輪矩陣約 70 分鐘
- `stop` 後約 US$16/月（磁碟）；`down` 後 0；Cloud Run 網站小流量在免費額度內
