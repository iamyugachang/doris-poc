# topology

## Purpose
定義本 POC 的 Doris 叢集拓撲：GCP asia-east1 三個 zone 各一台 VM，每台同時跑一個 FE（FOLLOWER）與一個 BE，資料三副本、FE 多數決選主，以及節點自動啟動與歸隊的行為契約。

## Requirements

### Requirement: 三節點單叢集拓撲
系統 SHALL 以一個 Doris 叢集運作：3 台 VM（doris-1/2/3，zone asia-east1-a/b/c）各跑 1 個 FE 與 1 個 BE；3 個 FE 皆為 FOLLOWER 角色，任一時刻恰有 1 個 master；3 個 BE 組成單一資料池，BE 之間沒有主從。FE 與 BE 同機是 POC 的成本取捨，不是拓撲要求。

#### Scenario: 叢集健康
- **WHEN** 三台 VM 皆運行且 FE/BE 服務已啟動
- **THEN** `SHOW FRONTENDS` 回 3 列、`Alive=true`、`Join=true`，恰有 1 列 `IsMaster=true`；`SHOW BACKENDS` 回 3 列 `Alive=true`

### Requirement: FE 多數決與自動選主
FE 層 SHALL 以 BDB JE 多數決維護 metadata：3 個 FOLLOWER 需至少 2 個存活才能選出 master 與寫入 metadata。master 消失時剩餘 FE MUST 自動選出新 master，不需人工介入。任一存活 FE SHALL 接受 client 連線並執行查詢；寫入由該 FE 轉發給 master。

#### Scenario: master 所在節點消失
- **WHEN** master FE 所在 VM 被停機，另外 2 個 FE 存活
- **THEN** 30 秒內選出新 master；期間 SELECT 照常，寫入可能失敗 1～2 次後恢復

#### Scenario: FE 缺乏多數
- **WHEN** 3 個 FE 只剩 1 個存活
- **THEN** 系統 SHALL NOT 選出 master；metadata 寫入與需要 master 的操作失敗；此狀態下的查詢可用性由 fault-scenarios 的實驗決定

### Requirement: 資料三副本與寫入多數決
測試表 SHALL 以 `replication_num=3` 建立，每個 tablet 的 3 份副本各落在一個 zone。寫入 SHALL 在至少 2 份副本成功時才回報成功；讀取只需任一副本存活。

#### Scenario: 一台 BE 離線
- **WHEN** 3 個 BE 中 1 個離線
- **THEN** `ADMIN SHOW REPLICA STATUS` 顯示 8 OK / 4 DEAD（4 buckets × 3 副本）；INSERT/UPSERT/DELETE/SELECT 照常；叢集無第四台可補副本，維持降級可用

#### Scenario: BE 回來後副本補齊
- **WHEN** 離線的 BE 重新上線
- **THEN** 60 秒內副本回到 12 OK，資料筆數與離線前的寫入一致，無遺失

### Requirement: 服務端點與網路邊界
FE SHALL 在 9030 提供 MySQL 協定、8030 HTTP、8070 Arrow Flight SQL；BE SHALL 在 9050 心跳、8050 Arrow Flight。VPC 內節點與 client 之間 SHALL 全埠互通；來自 VPC 外的 9030/8030/8040 MUST 只放行操作者 IP。

#### Scenario: VPC 外未授權來源
- **WHEN** 非操作者 IP 連 FE 9030
- **THEN** 連線被防火牆丟棄

### Requirement: 節點自動啟動與歸隊
FE 與 BE SHALL 由 systemd 管理並開機自啟；VM 重新啟動後節點 MUST 自動以 follower 身分歸隊、BE 自動恢復心跳，不需人工執行任何指令。

#### Scenario: VM 停機後重新啟動
- **WHEN** 一台 VM 由 TERMINATED 變為 RUNNING
- **THEN** 90 秒內該 FE `Alive=true`、該 BE `Alive=true`、副本全部 OK
