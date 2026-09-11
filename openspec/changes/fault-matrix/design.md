## Context

環境契約見 specs/topology、clients、operations：4 台 VM 由 Terraform 管、Doris 與探測由 Ansible 部署、demo.sh 負責動作。`break` 目前的契約只涵蓋「找出 master 所在 VM 並 `gcloud compute instances stop`」；狀態檔只記一個目標；`measure` 只算中斷視窗與失敗數。所有故障情境尚未執行，本文件只定義怎麼做與預期什麼。FE/BE 皆為 systemd 服務（`Restart=on-failure`, `RestartSec=10`），探測逾時 connect 3s / read-write 8s。動機見 proposal.md。

## Goals / Non-Goals

**Goals:**
- 一個 `break` 指令涵蓋 對象 × 方式 × 位置，可疊加；一個 `restore` 全部逆轉
- 每格實驗的結果可以用同一套 `measure` 得到「可用性等級 + 中斷秒數」
- 注入方式貼近真實故障：崩潰（自動拉起）、死透（等人）、卡住（不回應）

**Non-Goals:**
- 網路分割、zone 故障、時間偏移
- 調整 Doris 的選主 / 心跳參數

## Decisions

1. **注入手段對應真實故障**
   - crash → `kill -9 <pid>`：模擬程序崩潰；systemd 10 秒後拉起，觀察自動恢復
   - dead → `systemctl stop doris-fe|doris-be`：明確停止不觸發 `Restart=on-failure`，模擬程序死透待人工處理
   - hang → `kill -STOP <pid>` / 恢復 `kill -CONT`：模擬卡死；程序仍在、埠仍 listen，client 只能等逾時。這是三種裡對 client 最痛的，必須單獨一格
   - stop → 維持 `gcloud compute instances stop`
   - 替代方案：用 `iptables` 丟包模擬 hang。否決：那是網路故障，語意不同，留給下個 change
2. **位置解析在 client 端做**：`--on master` 以 `SHOW FRONTENDS` 找 `IsMaster=true` 的主機；`--on follower` 取第一個非 master；`--on <vm>` 直接指定。BE 沒有主從，`--target be` 的 `master|follower` 意思是「master FE 所在那台的 BE / 其他台的 BE」，讓 BE 故障可以跟 FE 故障對齊在同一台或不同台
3. **狀態檔改成可疊加的列表**：`.state/faults`，每行 `<ts> <target> <mode> <vm>`；`restore` 從最後一行往前逆轉。替代方案：每種故障各自的 restore 指令。否決：demo 時容易漏掉某一步
4. **可用性等級的判定放在 `measure`（讀 log），不在 client 端**：client 只忠實記錄 OK/FAIL；等級由最後一段時間的成功率推出。判定窗口 = 最後一個 EVENT 之後的紀錄，若不足 30 秒則取最後 30 秒
5. **crash 的自動恢復也記 EVENT**：`break --mode crash` 之後由 demo.sh 輪詢該服務 `ActiveEnterTimestamp`，拉起時寫入 `EVENT recovered: <target> restarted by systemd`，讓時間軸完整
6. **雙重故障用「連續 break」而非新指令**：組合數多，用參數疊加最省；spec 的每個雙重 Scenario 對應一組 break 序列
7. **矩陣執行器**：`experiments/scenarios.yaml` 定義每格（名稱、client 主機順序、break 序列、觀察秒數），`experiments/run_matrix.py --pass N` 逐格執行 monitor → baseline → break → 觀察 → restore → 等健康 → measure，結果寫 `results/pass-N/<id>/`；一格失敗就記錄並嘗試 restore + 健康檢查再往下，不中止整輪。三輪各自以 `start` 開始、`stop` 結束。替代方案：手動逐格。否決：60 次人工操作不可靠
8. **實測段落由工具回填**：`experiments/fill_results.py` 讀 results/ 彙整，寫進 delta spec 每個 Scenario 的 THEN 之後（三輪等級、中斷秒數、log 檔名），並產生 results.html 與 index.html 的矩陣表。spec 的設計文字不由工具改動

## 預期矩陣（等級 = 讀寫正常 / 只讀 / 不可用；全部待實驗驗證）

| 對象 | crash | dead | hang | stop |
|---|---|---|---|---|
| FE（master 所在） | 讀寫正常，短暫中斷 | 讀寫正常，FE 無冗餘 | 讀寫正常，中斷較長 | 讀寫正常，預期 ≤ 5s（連 follower 時可能因逾時拉長） |
| FE（follower 所在） | 讀寫正常，只影響連在它上的 client | 同左 | 同左，逾時後換台 | 讀寫正常，master 不變 |
| BE | 讀寫正常，1 次逾時 | 讀寫正常（副本 2/3） | 讀寫正常，中斷較長 | — |
| VM 停 + 另一 FE dead | — | 只讀 或 不可用（待測） | — | — |
| VM 停 + 另一 BE dead | — | 只讀 | — | — |
| 兩台 VM 停 | — | — | — | 只讀 或 不可用（待測） |

## Risks / Trade-offs

- [hang 情境 client 逾時 8 秒可能放大中斷秒數] → 報告中把「client 逾時等待」與「叢集選主時間」分開描述；探測逾時值列為假設
- [kill -STOP 的 FE 仍持有 BDB 鎖，可能延長選主] → 這正是要觀察的，記錄 `SHOW FRONTENDS` 變化時間
- [雙重故障後 `restore` 順序錯誤導致 FE 無法歸隊] → 逆序逆轉；若 FE 起不來，記錄並以 `ansible --limit <vm>` 修復
- [crash 的 systemd 拉起與 restore 競態] → restore 對 crash 只做健康確認，不重複啟動
- [BE dead 期間探測寫入不斷失敗會讓 key 一直前進] → 屬預期；每次失敗換新 key 不影響一致性驗證

## Open Questions（實驗後回答）

- FE 剩 1/3 時 SELECT 是否可用 → **不可用**。三輪一致：僅存的 FE 若是 follower 直接拒絕連線（catalog not ready）；若是 master 則接受連線但 INSERT 與 SELECT 都 8 秒逾時。FE 少於 2 個時查詢也拿不到 metadata。
- client 連在 follower 時，寫入轉發給已消失 master 的等待時間 → **會**。整台 VM 停機約需 25 秒，這段期間 follower 把寫入轉發給快消失的 master，每筆等 8 秒逾時；碰到就拉到 20～40 秒，沒碰到就 0～2 秒，三輪的範圍如實呈現。
- hang 情境下 Doris FE 判定 master 失聯的秒數 → **不穩定**：第 1 輪 120 秒內沒有重新選主（jdbc 卡住 138 秒直到人工恢復），第 2、3 輪約 63 秒後選出新 master。BDB JE 的心跳只看 TCP 連線是否存活，程序被 SIGSTOP 時 socket 還在，偵測時間取決於何時有需要回應的流量逾時。這是本實驗最值得追的後續題目（調 `bdbje_heartbeat_timeout_second` 或加外部 watchdog）。
- BE hang → FE 於約 27～37 秒後把該 BE 標為 DEAD 並改派副本，三輪一致（對應 BE 心跳逾時）。
