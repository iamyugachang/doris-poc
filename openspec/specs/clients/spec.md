# clients

## Purpose
定義三個探測 client（mysql、jdbc、arrow-flight）的行為契約：如何連線與 failover、每秒做什麼操作、如何驗證資料、如何記錄與量測，讓每種故障情境的結果可以用同一把尺比較。

## Requirements

### Requirement: 多主機清單連線，不經 Load Balancer
每個 client SHALL 持有 3 個 FE 的主機清單，連線時依序嘗試，第一個可連者即使用；不使用 Load Balancer 或 DNS。連線或操作失敗時 client MUST 關閉現有連線並重新依清單順序連線。jdbc client 的 failover MAY 由 driver 的多主機 URL 承擔，其餘 client 自行實作。

#### Scenario: 第一台 FE 不可連
- **WHEN** 清單第一台 FE 拒絕連線或逾時
- **THEN** client 在 connect timeout（3 秒）內改連下一台，不需修改設定

#### Scenario: 操作中連線中斷
- **WHEN** 進行中的操作收到連線重設、逾時或轉發 master 失敗
- **THEN** 該操作記為失敗；client 重連後從新的 key 由 INSERT 重新開始循環

### Requirement: 探測循環與資料驗證
每個 client SHALL 每秒執行一步，對同一把 key 依序執行 INSERT(ver=1) → UPSERT(ver=2) → SELECT → DELETE → SELECT，每完成一輪換下一把 key；各 client 使用互不重疊的 key 區段。SELECT 步驟 MUST 核對上一步的結果（UPSERT 後 ver=2、DELETE 後不存在），不符即記為失敗。測試表 SHALL 為 UNIQUE KEY（merge-on-write）模型，使同 key 的 INSERT 即 UPSERT。

#### Scenario: 正常循環
- **WHEN** 叢集健康
- **THEN** 每 5 秒完成一輪，表總筆數回到基準值 + 1（進行中那筆），0 次驗證失敗

#### Scenario: 協定不支援 DML
- **WHEN** client 第一次連線時以哨兵 key 試做 INSERT + DELETE 並讀回驗證，任一步失敗
- **THEN** client 記錄「DML unsupported … switching to SELECT-only mode」並改為每秒 SELECT 種子列（id=1）；報告中該 client 只代表讀取可用性

### Requirement: 三種協定
系統 SHALL 同時運行三個 client：mysql（MySQL 協定，FE:9030）、jdbc（JDBC 多主機 URL，FE:9030，`failOverReadOnly=false`）、arrow-flight（Arrow Flight SQL，FE:8070，結果由 BE:8050 取回）。三者 SHALL 跑在同一 VPC 的 client VM 上，各自一個 systemd 服務、各自一份 log。

#### Scenario: 三個 client 同時運行
- **WHEN** `monitor` 啟動探測
- **THEN** 三個服務皆 active，各自 log 出現 `PROBE start`，且在叢集健康時三者皆 0 失敗

### Requirement: 紀錄格式與量測定義
每個 client 的 log SHALL 每行以 `HH:MM:SS` 起頭，操作行為 `#<n> OK|FAIL <OP> id=<key> via <fe-name> …`，重連行為 `connected to <fe-name>`，故障注入與恢復由操作工具寫入 `EVENT …` 行。量測 SHALL 定義為：中斷視窗 = 第一次 FAIL 到下一次 OK 的秒數；失敗操作數依 OP 分類；重連次數 = `connected to` 行數減 1。所有 log 的時區 MUST 與操作者一致。

#### Scenario: 產出量測
- **WHEN** 執行 `measure`
- **THEN** 對每個 client 印出：起訖時間、失敗操作數（依類型）、重連次數、每個中斷視窗的起訖與秒數、EVENT 時間軸
