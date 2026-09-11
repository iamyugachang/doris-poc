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
`break` SHALL 找出當下的 FE master 所在 VM 並整台停機，並在三份 log 寫入 `EVENT break …` 行；被停機的目標 SHALL 記錄於狀態檔供 `restore` 使用。

#### Scenario: 停掉 master 所在 VM
- **WHEN** 執行 `break`
- **THEN** 該 VM 變為 TERMINATED，log 出現 `EVENT break: gcloud stop <vm> (FE master)` 與 `EVENT break: <vm> is down`

### Requirement: 恢復
`restore` SHALL 逆轉最近一次 `break`：啟動該 VM，等待 FE/BE 歸隊與副本全部 OK，寫入 `EVENT restore …` 行，並印出叢集狀態。

#### Scenario: 恢復停機的 VM
- **WHEN** 執行 `restore`
- **THEN** 300 秒內叢集回到健康（3 FE alive、3 BE alive、副本全 OK），否則以錯誤結束並說明尚未健康的項目

### Requirement: 量測
`measure` SHALL 從 client VM 取回三份 log，對每個 client 依 clients spec 的定義計算並印出結果，最後附叢集狀態。

#### Scenario: 產出報告
- **WHEN** 執行 `measure`
- **THEN** 印出三段（mysql / jdbc / flight）各含失敗數、重連數、中斷視窗、EVENT 時間軸

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
