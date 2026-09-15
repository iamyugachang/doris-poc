## Context

環境契約見 specs/topology、clients、operations：3 台 Doris VM（各 1 FE + 1 BE）+ 1 台 client VM（三個探測），demo.sh 負責 break / restore / measure。目前 `break` 只會停 master 所在 VM。本文件定義故障矩陣怎麼跑、預期什麼；實測數字放在 results/ 與 results.html，不寫進設計文件。

## Goals / Non-Goals

**Goals**
- 一個 `break` 涵蓋 對象 × 方式 × 位置，可疊加；一個 `restore` 全部逆轉
- 每格用同一套 `measure` 得到「可用性等級 + 中斷秒數」
- 注入方式貼近真實故障：crash（自動拉起）、dead（等人）、hang（不回應）

**Non-Goals**
- 網路分割、zone 故障、時間偏移
- 調整 Doris 選主 / 心跳參數

## Decisions

1. **注入手段對應真實故障**：crash = `kill -9`（systemd 10 秒後拉起）；dead = `systemctl stop`（不自動起）；hang = `kill -STOP`（程序在、埠在、不回應）；stop = `gcloud compute instances stop`。不用 iptables 模擬 hang，那是網路故障。
2. **位置在 client 端解析**：`--on master` 由 `SHOW FRONTENDS` 找 `IsMaster=true`；`--on follower` 取第一個非 master；BE 的 master / follower 指「與 master FE 同台 / 不同台的 BE」。
3. **狀態檔可疊加**：`.state/faults` 每行一個故障，`restore` 從最後一行逆序逆轉。
4. **等級由 `measure` 讀 log 判定**：client 只記 OK / FAIL；判定窗口 = 最後一個 EVENT 之後，不足 30 秒取最後 30 秒。
5. **crash 的自動拉起也記 EVENT**，時間軸才完整。
6. **雙重故障 = 連續 break**，不另設指令。
7. **矩陣執行器**：`experiments/scenarios.yaml` 定義每格，`experiments/run_matrix.py --pass N` 逐格跑 monitor → baseline → break → 觀察 → measure → restore → settle → measure，結果寫 `results/pass-N/<id>/`；一格失敗記錄後繼續。
8. **設計與結果分離**：`experiments/fill_results.py` 只彙整 results/ 成 `results/summary.json`，供 results.html 與 index.html 使用；spec 與 design 不放實測。

## 預期矩陣（假設，待實驗驗證）

| 對象 | crash | dead | hang | stop |
|---|---|---|---|---|
| FE（master 所在） | 讀寫正常，短暫中斷 | 讀寫正常，FE 無冗餘 | 讀寫正常，中斷較長 | 讀寫正常，≤ 5s |
| FE（follower 所在） | 讀寫正常，只影響連在它上的 client | 同左 | 同左，逾時後換台 | 讀寫正常，master 不變 |
| BE | 讀寫正常，1 次逾時 | 讀寫正常（副本 2/3） | 讀寫正常，中斷較長 | — |
| VM 停 + 另一 FE dead | — | 只讀 或 不可用 | — | — |
| VM 停 + 另一 BE dead | — | 只讀 | — | — |
| 兩台 VM 停 | — | — | — | 只讀 或 不可用 |

## Risks / Trade-offs

- hang 情境含 client 8 秒逾時 → 報告把「client 逾時」與「叢集選主」分開描述
- `kill -STOP` 的 FE 仍持有 BDB 鎖，可能延長選主 → 正是要觀察的
- 雙重故障 restore 順序錯會讓 FE 無法歸隊 → 逆序逆轉；起不來就 `ansible --limit <vm>` 修
- crash 的 systemd 拉起與 restore 競態 → restore 對 crash 只做健康確認

## Open Questions（由實驗回答，答案見 results.html）

- FE 剩 1/3 時 SELECT 是否可用？
- client 連在 follower 時，寫入轉發給已消失的 master 會等多久？
- master FE hang 後，其他 FE 多久判定失聯並重新選主？
- BE hang 後，FE 多久把它標為 DEAD？
