# operations

## Purpose
定義操作工具（demo.sh 與底層 Terraform / Ansible）對外的行為契約：建立、監控、故障注入、恢復、量測、關機與清除，以及 dry-run 與成本邊界，讓實驗可以被任何人重複執行。

## Requirements

### Requirement: 可重複的建立
`up` SHALL 建立或修復完整環境：4 台 VM 與防火牆（Terraform）、Doris 安裝與叢集組成、三個探測 client（Ansible）、測試表與 1 萬筆種子資料。重複執行 MUST 不破壞既有資料，且在環境已完整時不產生變更。

#### Scenario: 全新專案
- **WHEN** 專案內沒有任何資源
- **THEN** `up` 結束時 3 FE / 3 BE alive、副本 12 OK、client VM 上三個探測服務已安裝

#### Scenario: 重複執行
- **WHEN** 環境已完整
- **THEN** Terraform 無變更、Ansible `changed=0`、資料筆數不變

### Requirement: 監控
`monitor` SHALL 在 client VM 啟動三個探測（清空舊 log）並即時合併顯示三份 log，前綴標明 client；離開顯示不停止探測。探測 SHALL 持續運行直到 `stop`、`down` 或明確停止。

#### Scenario: 啟動監控
- **WHEN** 執行 `monitor`
- **THEN** 三個探測服務 active，畫面每秒各出現一行 `[mysql] / [jdbc] / [flight]`

### Requirement: 故障注入
`break` SHALL 依參數注入故障：對象 `--target fe|be|vm`（預設 vm）、方式 `--mode crash|dead|hang|stop`（fe/be 預設 crash，vm 只有 stop）、位置 `--on master|follower|<vm-name>`（預設 master）。每次注入 MUST 在三份 client log 寫入 `EVENT break: <target> <mode> on <vm> (<role>)`，並把故障追加到狀態檔；連續執行 `break` SHALL 疊加故障而不覆蓋前一次。

#### Scenario: 停掉 master 所在 VM
- **WHEN** 執行 `break` 不帶參數（等同 `--target vm --mode stop --on master`）
- **THEN** 該 VM 變為 TERMINATED，log 出現 `EVENT break: vm stop on <vm> (FE master)` 與 `EVENT break: <vm> is down`

#### Scenario: 讓 master FE 崩潰
- **WHEN** 執行 `break --target fe --mode crash --on master`
- **THEN** 該 FE 程序被 kill -9，systemd 於 10 秒內拉起；log 出現對應 EVENT 行；狀態檔記錄此故障

#### Scenario: 讓 BE 死透
- **WHEN** 執行 `break --target be --mode dead --on follower`
- **THEN** 該 BE 被 systemctl stop 且不自動重啟，直到 `restore`

#### Scenario: 讓程序卡住
- **WHEN** 執行 `break --target fe --mode hang --on master`
- **THEN** 該 FE 程序收到 SIGSTOP，仍出現在程序列表但不回應任何連線

#### Scenario: 疊加雙重故障
- **WHEN** 先 `break`（VM stop）再 `break --target fe --mode dead --on follower`
- **THEN** 狀態檔含兩筆故障，`status` 顯示 FE 1/3 alive

### Requirement: 恢復
`restore` SHALL 依注入的相反順序逆轉狀態檔中的全部故障（VM start、systemctl start、kill -CONT），每一步寫入 `EVENT restore: …`，最後等待叢集健康並印出狀態；crash 方式的故障 MAY 已被 systemd 自動恢復，`restore` 對其只做健康確認。

#### Scenario: 恢復停機的 VM
- **WHEN** 狀態檔只含一筆「VM stop」，執行 `restore`
- **THEN** 300 秒內叢集回到健康（3 FE alive、3 BE alive、副本全 OK），否則以錯誤結束並說明尚未健康的項目

#### Scenario: 逆轉雙重故障
- **WHEN** 狀態檔含「VM stop」與「FE dead」兩筆
- **THEN** 先 systemctl start 該 FE，再 start VM；300 秒內叢集健康，狀態檔清空

### Requirement: 量測
`measure` SHALL 在原有輸出之外，對每個 client 判定可用性等級：取 log 最後 30 秒（或最後一個 EVENT 之後）各操作的成功率，寫入 / 讀取皆成功 ⇒ 讀寫正常；SELECT 成功但任一寫入持續失敗 ⇒ 只讀；SELECT 持續失敗 ⇒ 不可用。arrow-flight client 只判定讀取。

#### Scenario: 產出報告
- **WHEN** 執行 `measure`
- **THEN** 印出三段（mysql / jdbc / flight）各含失敗數、重連數、中斷視窗、EVENT 時間軸，以及一行可用性等級摘要

#### Scenario: 只讀狀態的報告
- **WHEN** BE 剩 1/3 時執行 `measure`
- **THEN** mysql 與 jdbc 顯示「只讀（INSERT/UPSERT/DELETE 失敗中）」，arrow-flight 顯示「讀取正常」

### Requirement: 關機、開機與清除
`stop` / `start` SHALL 透過 `vm_status` 變數關閉 / 開啟全部 4 台 VM，保留磁碟；`start` 後叢集 MUST 自動回到健康。`down` SHALL 刪除 VM 與防火牆（保留已啟用的 API 與 Cloud Run 網站），且 MUST 要求明確確認。

#### Scenario: 關機省錢
- **WHEN** 執行 `stop`
- **THEN** 4 台 VM 皆 TERMINATED，探測已停止，費用只剩磁碟

#### Scenario: 清除
- **WHEN** 執行 `down` 並輸入 `delete`
- **THEN** 專案內不再有 doris-* VM 與 doris-client-from-me 防火牆

### Requirement: 預演
任何指令加 `--dry-run` SHALL 只印出將執行的 gcloud / terraform / ansible 指令而不變更任何資源；`plan` SHALL 印出 Terraform plan 與 Ansible check/diff。

#### Scenario: dry-run
- **WHEN** 執行 `auto --dry-run`
- **THEN** 印出完整流程的指令，GCP 資源與 log 均無變化

### Requirement: 成本邊界
運行中的完整環境 SHALL 約 US$0.51/小時（3 × e2-standard-4 + e2-small + 170 GB pd-balanced）；`stop` 後約 US$16/月；`down` 後 0。Cloud Run 網站在小流量下 SHALL 落在免費額度。

#### Scenario: 一輪 demo 的花費
- **WHEN** 從 `start` 到 `stop` 約 15 分鐘
- **THEN** 費用約 US$0.15
