## Purpose
定義本實驗的故障矩陣：每個故障情境的注入方式、預期的可用性等級（讀寫正常 / 只讀 / 不可用）與三個 client 的觀察點。所有 Scenario 目前只有預期；實驗跑完後在各 Scenario 的 THEN 之後補「實測」段落（日期、數字、log 檔名）。

## ADDED Requirements

### Requirement: 可用性等級
每個故障情境的結果 SHALL 以三個等級之一描述：**讀寫正常**（INSERT/UPSERT/DELETE/SELECT 在中斷視窗後全部恢復）、**只讀**（SELECT 持續可用，寫入持續失敗）、**不可用**（SELECT 亦持續失敗）。中斷視窗內的暫時失敗不改變等級。等級 SHALL 由 FE 與 BE 各自的多數決推導：FE 存活 < 2 ⇒ 寫入不可用；BE 存活 < 2 ⇒ 寫入不可用；兩者皆 ≥ 2 ⇒ 讀寫正常。

#### Scenario: 等級判定
- **WHEN** 故障注入後觀察至少 60 秒
- **THEN** 依最後 30 秒（或最後一個 EVENT 之後）各操作的成功與否判定等級，並記錄中斷視窗秒數、各操作失敗數、重連數

#### Scenario: 每格三輪
- **WHEN** 執行矩陣
- **THEN** 每個 Scenario 在三個獨立的輪次各跑一次（每輪從全部 VM 重新開機開始，結束後全部關機）；實測段落記錄三輪的等級與中斷秒數，等級以三輪中最差者為準

### Requirement: 單一 VM 停機
當一台 VM 整台停機（該台 FE 與 BE 一起消失）時，系統 SHALL 維持**讀寫正常**：FE 剩 2/3 可選主，BE 剩 2/3 可寫。

#### Scenario: master 所在 VM 停機，client 直連 master
- **WHEN** client 連在 master FE 上，該 VM 被 `gcloud compute instances stop`
- **THEN** 連線立即被重設，client 換台後 5 秒內恢復；寫入失敗 ≤ 2 次；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 37s，最長無回應 12s；restore 期間 0s；全程失敗 7：SELECT×1/INSERT×4/DELETE×1/UPSERT×1）；jdbc 讀寫正常（故障中受影響 39s，最長無回應 22s；restore 期間 0s；全程失敗 6：SELECT×1/INSERT×4/UPSERT×1）；flight 讀取正常（故障中受影響 30s，最長無回應 29s；restore 期間 0s；全程失敗 2：SELECT×2）；故障中 FE 2/3 (master doris-3) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10016 via doris-1；log `results/pass-1/vm-stop-master-direct/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 4s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 1：DELETE×1）；故障中 FE 2/3 (master doris-3) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10067 via doris-1；log `results/pass-2/vm-stop-master-direct/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-3) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10117 via doris-1；log `results/pass-3/vm-stop-master-direct/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 0～37s、jdbc 1～39s、flight 0～30s

#### Scenario: master 所在 VM 停機，client 連在 follower
- **WHEN** client 連在 follower FE 上，master 所在 VM 被停機
- **THEN** 寫入因轉發給已消失的 master 而失敗，選主完成後恢復；SELECT 照常；觀察點：client 是否因等待逾時而拉長中斷；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：UPSERT×1）；jdbc 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10020 via doris-1；log `results/pass-1/vm-stop-master-follower/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 28s，最長無回應 9s；restore 期間 0s；全程失敗 7：INSERT×5/SELECT×2）；jdbc 讀寫正常（故障中受影響 32s，最長無回應 31s；restore 期間 0s；全程失敗 4：SELECT×2/INSERT×2）；flight 讀取正常（故障中受影響 30s，最長無回應 9s；restore 期間 0s；全程失敗 6：SELECT×6）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10067 via doris-1；log `results/pass-2/vm-stop-master-follower/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10120 via doris-1；log `results/pass-3/vm-stop-master-follower/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 0～28s、jdbc 2～32s、flight 1～30s

#### Scenario: follower 所在 VM 停機
- **WHEN** 非 master 的 VM 被停機
- **THEN** master 不變；只有連在該 FE 的 client 需要重連；副本 8 OK / 4 DEAD；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 25s，最長無回應 12s；restore 期間 0s；全程失敗 3：UPSERT×1/INSERT×2）；jdbc 讀寫正常（故障中受影響 19s，最長無回應 16s；restore 期間 0s；全程失敗 3：INSERT×3）；flight 讀取正常（故障中受影響 20s，最長無回應 18s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10023 via doris-2；log `results/pass-1/vm-stop-follower/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10068 via doris-2；log `results/pass-2/vm-stop-follower/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 12s，最長無回應 9s；restore 期間 0s；全程失敗 2：INSERT×2）；jdbc 讀寫正常（故障中受影響 14s，最長無回應 11s；restore 期間 0s；全程失敗 2：SELECT×1/INSERT×1）；flight 讀取正常（故障中受影響 18s，最長無回應 18s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10124 via doris-2；log `results/pass-3/vm-stop-follower/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 0～25s、jdbc 2～19s、flight 2～20s

#### Scenario: 三個 client 同時觀察 VM 停機
- **WHEN** mysql / jdbc / arrow-flight 三個 client 在 VPC 內同時運行，master 所在 VM 被停機
- **THEN** 三者皆在 5 秒內恢復（arrow-flight 只驗證讀取）；三份 log 的中斷視窗可互相對照
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 29s，最長無回應 9s；restore 期間 0s；全程失敗 5：INSERT×5）；jdbc 讀寫正常（故障中受影響 34s，最長無回應 32s；restore 期間 0s；全程失敗 3：SELECT×1/INSERT×2）；flight 讀取正常（故障中受影響 29s，最長無回應 9s；restore 期間 0s；全程失敗 5：SELECT×5）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10013 via doris-1；log `results/pass-1/vm-stop-3clients/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 4s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；jdbc 讀寫正常（故障中受影響 4s，最長無回應 0s；restore 期間 0s；全程失敗 2：DELETE×1/SELECT×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10062 via doris-1；log `results/pass-2/vm-stop-3clients/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 27s，最長無回應 9s；restore 期間 0s；全程失敗 6：SELECT×2/INSERT×4）；jdbc 讀寫正常（故障中受影響 34s，最長無回應 31s；restore 期間 0s；全程失敗 7：DELETE×1/SELECT×3/INSERT×3）；flight 讀取正常（故障中受影響 30s，最長無回應 9s；restore 期間 0s；全程失敗 5：SELECT×5）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas {'OK': 8, 'DEAD': 4} rows=10116 via doris-1；log `results/pass-3/vm-stop-3clients/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 4～29s、jdbc 4～34s、flight 2～30s

### Requirement: FE 程序故障
當單一 FE 程序 crash、dead 或 hang 而 VM 與 BE 仍正常時，系統 SHALL 維持**讀寫正常**；影響範圍取決於該 FE 是否為 master 以及 client 是否連在它上面。

#### Scenario: master FE crash（kill -9，systemd 自動拉起）
- **WHEN** master FE 程序被 kill -9，systemd 於 10 秒內重新啟動它
- **THEN** 剩餘 2 個 FE 選出新 master；連在該 FE 的 client 重連他台，寫入失敗 ≤ 2 次後恢復；被拉起的 FE 以 follower 歸隊；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 26s，最長無回應 9s；restore 期間 0s；全程失敗 2：DELETE×1/INSERT×1）；jdbc 讀寫正常（故障中受影響 29s，最長無回應 11s；restore 期間 0s；全程失敗 2：DELETE×2）；flight 讀取正常（故障中受影響 6s，最長無回應 6s；restore 期間 0s；全程失敗 0）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10027 via doris-1；log `results/pass-1/fe-crash-master/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 18s，最長無回應 9s；restore 期間 0s；全程失敗 2：INSERT×2）；jdbc 讀寫正常（故障中受影響 22s，最長無回應 11s；restore 期間 0s；全程失敗 11：DELETE×1/SELECT×5/INSERT×5）；flight 讀取正常（故障中受影響 6s，最長無回應 6s；restore 期間 0s；全程失敗 0）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10070 via doris-1；log `results/pass-2/fe-crash-master/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 24s，最長無回應 10s；restore 期間 0s；全程失敗 6：SELECT×2/INSERT×4）；jdbc 讀寫正常（故障中受影響 23s，最長無回應 11s；restore 期間 0s；全程失敗 4：DELETE×2/SELECT×1/INSERT×1）；flight 讀取正常（故障中受影響 8s，最長無回應 7s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10130 via doris-1；log `results/pass-3/fe-crash-master/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 18～26s、jdbc 22～29s、flight 6～8s

#### Scenario: follower FE crash
- **WHEN** 某 follower FE 程序被 kill -9
- **THEN** 只有連在該 FE 的 client 需要重連；master 不變；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 3s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10027 via doris-1；log `results/pass-1/fe-crash-follower/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；jdbc 讀寫正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：DELETE×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10073 via doris-1；log `results/pass-2/fe-crash-follower/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 3s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10133 via doris-1；log `results/pass-3/fe-crash-follower/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 1～2s、jdbc 1～3s、flight 2～3s

#### Scenario: master FE dead（systemctl stop，不自動起）
- **WHEN** master FE 被 systemctl stop 且不重啟
- **THEN** 選出新 master 後叢集以 2 個 FE 持續運作，`SHOW FRONTENDS` 該列 `Alive=false`；等級：讀寫正常，restore 前 FE 層無冗餘
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 28s，最長無回應 9s；restore 期間 0s；全程失敗 2：UPSERT×1/INSERT×1）；jdbc 讀寫正常（故障中受影響 27s，最長無回應 9s；restore 期間 0s；全程失敗 3：UPSERT×1/INSERT×2）；flight 讀取正常（故障中受影響 6s，最長無回應 6s；restore 期間 0s；全程失敗 0）；故障中 FE 2/3 (master doris-2) BE 3/3 replicas {'OK': 12} rows=10033 via doris-1；log `results/pass-1/fe-dead-master/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 22s，最長無回應 9s；restore 期間 0s；全程失敗 4：INSERT×3/SELECT×1）；jdbc 讀寫正常（故障中受影響 22s，最長無回應 9s；restore 期間 0s；全程失敗 3：SELECT×1/INSERT×2）；flight 讀取正常（故障中受影響 7s，最長無回應 6s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-2) BE 3/3 replicas {'OK': 12} rows=10077 via doris-1；log `results/pass-2/fe-dead-master/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 0s，最長無回應 0s；restore 期間 0s；全程失敗 0）；jdbc 讀寫正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 2：DELETE×1/SELECT×1）；flight 讀取正常（故障中受影響 9s，最長無回應 9s；restore 期間 0s；全程失敗 0）；故障中 FE 2/3 (master doris-2) BE 3/3 replicas {'OK': 12} rows=10134 via doris-1；log `results/pass-3/fe-dead-master/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 0～28s、jdbc 1～27s、flight 6～9s

#### Scenario: master FE hang（kill -STOP）
- **WHEN** master FE 程序被暫停（活著但不回應）
- **THEN** 連在該 FE 的 client 等到逾時（8 秒）才失敗並換台；其他 FE 在心跳逾時後判定 master 失聯並重新選主；觀察點：中斷視窗是否明顯長於 crash；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 只讀（由 flight 推斷）（故障中受影響 136s，最長無回應 10s；restore 期間 0s；全程失敗 15：INSERT×15）；jdbc 卡住（無回應）（故障中受影響 136s，最長無回應 136s；restore 期間 0s；全程失敗 0）；flight 讀取正常（故障中受影響 136s，最長無回應 10s；restore 期間 0s；全程失敗 0）；故障中 None；log `results/pass-1/fe-hang-master/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 63s，最長無回應 9s；restore 期間 0s；全程失敗 7：INSERT×7）；jdbc 讀寫正常（故障中受影響 69s，最長無回應 51s；restore 期間 0s；全程失敗 0）；flight 讀取正常（故障中受影響 63s，最長無回應 9s；restore 期間 0s；全程失敗 0）；故障中 FE 2/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10079 via doris-1；log `results/pass-2/fe-hang-master/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 64s，最長無回應 9s；restore 期間 0s；全程失敗 7：INSERT×7）；jdbc 讀寫正常（故障中受影響 69s，最長無回應 52s；restore 期間 0s；全程失敗 0）；flight 讀取正常（故障中受影響 63s，最長無回應 9s；restore 期間 0s；全程失敗 0）；故障中 FE 2/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10136 via doris-1；log `results/pass-3/fe-hang-master/`
- 實測 結論：卡住（無回應）（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 63～136s、jdbc 69～136s、flight 63～136s

#### Scenario: follower FE hang
- **WHEN** 某 follower FE 程序被暫停
- **THEN** 連在該 FE 的 client 逾時後換台，其他 client 無感；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 18s，最長無回應 9s；restore 期間 0s；全程失敗 1：SELECT×1）；jdbc 讀寫正常（故障中受影響 45s，最長無回應 9s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 39s，最長無回應 30s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10039 via doris-2；log `results/pass-1/fe-hang-follower/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 28s，最長無回應 10s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 48s，最長無回應 12s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 39s，最長無回應 30s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10082 via doris-2；log `results/pass-2/fe-hang-follower/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 20s，最長無回應 11s；restore 期間 0s；全程失敗 1：SELECT×1）；jdbc 讀寫正常（故障中受影響 48s，最長無回應 11s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 39s，最長無回應 30s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 2/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10138 via doris-2；log `results/pass-3/fe-hang-follower/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 18～28s、jdbc 45～48s、flight 39～39s

### Requirement: BE 程序故障
當單一 BE 程序 crash、dead 或 hang 而 FE 正常時，系統 SHALL 維持**讀寫正常**（副本 2/3）。

#### Scenario: BE crash（systemd 自動拉起）
- **WHEN** 某 BE 程序被 kill -9，systemd 於 10 秒內重新啟動它
- **THEN** FE 判定該 BE 死亡的瞬間可能有 1 次操作逾時；副本短暫 DEAD 後隨 BE 回來恢復 OK；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 19s，最長無回應 9s；restore 期間 0s；全程失敗 2：SELECT×1/INSERT×1）；jdbc 讀寫正常（故障中受影響 20s，最長無回應 9s；restore 期間 0s；全程失敗 1：DELETE×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 2：SELECT×2）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10040 via doris-1；log `results/pass-1/be-crash/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 18s，最長無回應 9s；restore 期間 0s；全程失敗 2：SELECT×1/INSERT×1）；jdbc 讀寫正常（故障中受影響 18s，最長無回應 10s；restore 期間 0s；全程失敗 2：DELETE×1/INSERT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10086 via doris-1；log `results/pass-2/be-crash/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 16s，最長無回應 9s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 15s，最長無回應 9s；restore 期間 0s；全程失敗 2：SELECT×1/INSERT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 3/3 replicas {'OK': 12} rows=10139 via doris-1；log `results/pass-3/be-crash/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 16～19s、jdbc 15～20s、flight 1～2s

#### Scenario: BE dead
- **WHEN** 某 BE 被 systemctl stop 且不重啟
- **THEN** 副本 8 OK / 4 DEAD，寫入以 2/3 副本成功，SELECT 照常；等級：讀寫正常（降級）
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 6s，最長無回應 6s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 6s，最長無回應 0s；restore 期間 0s；全程失敗 2：SELECT×1/INSERT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10044 via doris-1；log `results/pass-1/be-dead/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 9s，最長無回應 9s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 8s，最長無回應 8s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 1s，最長無回應 0s；restore 期間 0s；全程失敗 1：SELECT×1）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10089 via doris-1；log `results/pass-2/be-dead/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 7s，最長無回應 7s；restore 期間 0s；全程失敗 1：INSERT×1）；jdbc 讀寫正常（故障中受影響 7s，最長無回應 7s；restore 期間 0s；全程失敗 1：SELECT×1）；flight 讀取正常（故障中受影響 2s，最長無回應 0s；restore 期間 0s；全程失敗 2：SELECT×2）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10139 via doris-1；log `results/pass-3/be-dead/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 6～9s、jdbc 6～8s、flight 1～2s

#### Scenario: BE hang（kill -STOP）
- **WHEN** 某 BE 程序被暫停
- **THEN** 落在該 BE 副本上的查詢與寫入等到逾時才失敗，FE 於心跳逾時後標記 DEAD 並改派其他副本；觀察點：中斷視窗是否長於 dead；等級：讀寫正常
- 實測 第1輪 2026-09-11：mysql 讀寫正常（故障中受影響 28s，最長無回應 9s；restore 期間 0s；全程失敗 3：SELECT×1/INSERT×2）；jdbc 讀寫正常（故障中受影響 28s，最長無回應 9s；restore 期間 0s；全程失敗 3：SELECT×1/INSERT×2）；flight 讀取正常（故障中受影響 31s，最長無回應 9s；restore 期間 0s；全程失敗 4：SELECT×4）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10045 via doris-1；log `results/pass-1/be-hang/`
- 實測 第2輪 2026-09-11：mysql 讀寫正常（故障中受影響 27s，最長無回應 9s；restore 期間 0s；全程失敗 3：SELECT×1/INSERT×2）；jdbc 讀寫正常（故障中受影響 27s，最長無回應 9s；restore 期間 0s；全程失敗 3：DELETE×1/INSERT×2）；flight 讀取正常（故障中受影響 27s，最長無回應 9s；restore 期間 0s；全程失敗 3：SELECT×3）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10091 via doris-1；log `results/pass-2/be-hang/`
- 實測 第3輪 2026-09-11：mysql 讀寫正常（故障中受影響 37s，最長無回應 10s；restore 期間 0s；全程失敗 4：SELECT×2/INSERT×2）；jdbc 讀寫正常（故障中受影響 36s，最長無回應 9s；restore 期間 0s；全程失敗 4：DELETE×1/SELECT×1/INSERT×2）；flight 讀取正常（故障中受影響 31s，最長無回應 9s；restore 期間 0s；全程失敗 4：SELECT×4）；故障中 FE 3/3 (master doris-3) BE 2/3 replicas {'DEAD': 4, 'OK': 8} rows=10141 via doris-1；log `results/pass-3/be-hang/`
- 實測 結論：讀寫正常（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 27～37s、jdbc 27～36s、flight 27～31s

### Requirement: 雙重故障
當兩個元件同時故障時，系統的可用性等級 SHALL 依可用性等級 Requirement 的多數決規則推導；SELECT 在 BE 存活 ≥ 1 且任一 FE 可服務時 MAY 仍可用，是否真的可用由實驗決定。

#### Scenario: VM 停 + 另一台 FE dead（FE 剩 1/3）
- **WHEN** master 所在 VM 停機後，再把剩餘 2 個 FE 之一 systemctl stop
- **THEN** 無法選出 master，INSERT/UPSERT/DELETE 全部失敗；SELECT 是否可用為本格的主要觀察點（剩餘 FE 記憶體內仍有 metadata）；預期等級：只讀或不可用
- 實測 第1輪 2026-09-11：mysql 不可用（故障中受影響 102s，最長無回應 12s；restore 期間 0s；全程失敗 32：DELETE×1/INSERT×31）；jdbc 卡住（無回應）（故障中受影響 104s，最長無回應 55s；restore 期間 0s；全程失敗 8：SELECT×2/INSERT×6）；flight 讀取失敗（故障中受影響 75s，最長無回應 22s；restore 期間 0s；全程失敗 14：SELECT×14）；故障中 FE 0/3? BE ?/3 (no FE reachable: no FE reachable: (2003, "Can't connect to MySQL server on '35.185.162.157' ([Errno 111] Connection refused)"))；log `results/pass-1/double-vm-fe-dead/`
- 實測 第2輪 2026-09-11：mysql 不可用（故障中受影響 133s，最長無回應 9s；restore 期間 0s；全程失敗 58：UPSERT×1/SELECT×13/INSERT×44）；jdbc 不可用（故障中受影響 139s，最長無回應 32s；restore 期間 0s；全程失敗 53：INSERT×45/SELECT×8）；flight 讀取失敗（故障中受影響 134s，最長無回應 10s；restore 期間 0s；全程失敗 26：SELECT×26）；故障中 FE 1/3 (master doris-2) BE 2/3 replicas n/a rows=None via doris-2；log `results/pass-2/double-vm-fe-dead/`
- 實測 第3輪 2026-09-11：mysql 不可用（故障中受影響 106s，最長無回應 9s；restore 期間 0s；全程失敗 58：INSERT×51/SELECT×7）；jdbc 不可用（故障中受影響 108s，最長無回應 12s；restore 期間 0s；全程失敗 52：SELECT×8/INSERT×44）；flight 讀取失敗（故障中受影響 107s，最長無回應 10s；restore 期間 0s；全程失敗 27：SELECT×27）；故障中 FE 2/3 (master doris-2) BE 2/3 replicas n/a rows=None via doris-2；log `results/pass-3/double-vm-fe-dead/`
- 實測 結論：不可用（mysql/jdbc 三輪最差），arrow-flight 讀取失敗；影響（失敗＋卡頓）mysql 102～133s、jdbc 104～139s、flight 75～134s

#### Scenario: VM 停 + 另一台 BE dead（BE 剩 1/3）
- **WHEN** 一台 VM 停機後，再把剩餘 2 個 BE 之一 systemctl stop
- **THEN** 寫入因無法達到 2/3 副本而失敗；SELECT 由僅存副本服務、照常；預期等級：只讀
- 實測 第1輪 2026-09-11：mysql 只讀（由 flight 推斷）（故障中受影響 99s，最長無回應 0s；restore 期間 0s；全程失敗 118：SELECT×1/INSERT×117）；jdbc 只讀（由 flight 推斷）（故障中受影響 103s，最長無回應 0s；restore 期間 0s；全程失敗 122：SELECT×2/INSERT×120）；flight 讀取正常（故障中受影響 40s，最長無回應 0s；restore 期間 0s；全程失敗 63：SELECT×63）；故障中 FE 2/3 (master doris-2) BE 1/3 replicas {'DEAD': 8, 'OK': 4} rows=10054 via doris-1；log `results/pass-1/double-vm-be-dead/`
- 實測 第2輪 2026-09-11：mysql 只讀（故障中受影響 42s，最長無回應 9s；restore 期間 0s；全程失敗 134：INSERT×120/SELECT×14）；jdbc 只讀（故障中受影響 48s，最長無回應 31s；restore 期間 0s；全程失敗 136：SELECT×15/INSERT×121）；flight 讀取正常（故障中受影響 61s，最長無回應 9s；restore 期間 0s；全程失敗 65：SELECT×65）；故障中 FE 2/3 (master doris-2) BE 1/3 replicas {'DEAD': 8, 'OK': 4} rows=10099 via doris-1；log `results/pass-2/double-vm-be-dead/`
- 實測 第3輪 2026-09-11：mysql 只讀（故障中受影響 45s，最長無回應 9s；restore 期間 0s；全程失敗 131：SELECT×14/INSERT×117）；jdbc 只讀（故障中受影響 55s，最長無回應 31s；restore 期間 0s；全程失敗 144：DELETE×1/SELECT×19/INSERT×124）；flight 讀取正常（故障中受影響 59s，最長無回應 9s；restore 期間 0s；全程失敗 34：SELECT×34）；故障中 FE 2/3 (master doris-2) BE 1/3 replicas {'DEAD': 8, 'OK': 4} rows=10147 via doris-1；log `results/pass-3/double-vm-be-dead/`
- 實測 結論：只讀（mysql/jdbc 三輪最差），arrow-flight 讀取正常；影響（失敗＋卡頓）mysql 42～99s、jdbc 48～103s、flight 40～61s

#### Scenario: 兩台 VM 停（FE 1/3、BE 1/3）
- **WHEN** 兩台 VM 先後停機
- **THEN** 寫入失敗；SELECT 是否可用為觀察點；預期等級：只讀或不可用
- 實測 第1輪 2026-09-11：mysql 不可用（故障中受影響 128s，最長無回應 15s；restore 期間 0s；全程失敗 38：INSERT×37/DELETE×1）；jdbc 卡住（無回應）（故障中受影響 126s，最長無回應 91s；restore 期間 0s；全程失敗 4：SELECT×2/INSERT×2）；flight 讀取失敗（故障中受影響 124s，最長無回應 41s；restore 期間 0s；全程失敗 22：SELECT×22）；故障中 FE 0/3? BE ?/3 (no FE reachable: no FE reachable: (2003, "Can't connect to MySQL server on '34.80.234.205' ([Errno 111] Connection refused)"))；log `results/pass-1/double-two-vms/`
- 實測 第2輪 2026-09-11：mysql 不可用（故障中受影響 154s，最長無回應 16s；restore 期間 0s；全程失敗 42：INSERT×23/SELECT×19）；jdbc 卡住（無回應）（故障中受影響 150s，最長無回應 47s；restore 期間 0s；全程失敗 15：SELECT×7/INSERT×7/UPSERT×1）；flight 讀取失敗（故障中受影響 101s，最長無回應 41s；restore 期間 0s；全程失敗 12：SELECT×12）；故障中 FE 0/3? BE ?/3 (no FE reachable: no FE reachable: (2003, "Can't connect to MySQL server on '34.80.234.205' ([Errno 111] Connection refused)"))；log `results/pass-2/double-two-vms/`
- 實測 第3輪 2026-09-11：mysql 不可用（故障中受影響 129s，最長無回應 15s；restore 期間 0s；全程失敗 30：UPSERT×1/SELECT×15/DELETE×1/INSERT×13）；jdbc 卡住（無回應）（故障中受影響 126s，最長無回應 64s；restore 期間 0s；全程失敗 5：INSERT×3/SELECT×2）；flight 讀取卡住（故障中受影響 126s，最長無回應 47s；restore 期間 0s；全程失敗 7：SELECT×7）；故障中 FE 0/3? BE ?/3 (no FE reachable: no FE reachable: (2003, "Can't connect to MySQL server on '34.80.234.205' ([Errno 111] Connection refused)"))；log `results/pass-3/double-two-vms/`
- 實測 結論：不可用（mysql/jdbc 三輪最差），arrow-flight 讀取失敗；影響（失敗＋卡頓）mysql 128～154s、jdbc 126～150s、flight 101～126s

#### Scenario: 交錯故障（一台 VM 停、一台 BE dead、一台 FE dead）
- **WHEN** doris-1 VM 停、doris-2 的 BE stop、doris-3 的 FE stop
- **THEN** FE 剩 doris-2（1/3）、BE 剩 doris-3（1/3）；預期等級：只讀或不可用；用來驗證「等級由兩層各自的多數決決定」
- 實測 第1輪 2026-09-11：mysql 不可用（故障中受影響 146s，最長無回應 0s；restore 期間 0s；全程失敗 52：SELECT×1/UPSERT×1/INSERT×50）；jdbc 不可用（故障中受影響 148s，最長無回應 0s；restore 期間 0s；全程失敗 52：DELETE×2/INSERT×50）；flight 讀取失敗（故障中受影響 146s，最長無回應 22s；restore 期間 0s；全程失敗 23：SELECT×23）；故障中 alive check failed: OperationalError: (1105, 'Exception, msg: Failed to get master client.')；log `results/pass-1/double-crossed/`
- 實測 第2輪 2026-09-11：mysql 只讀（故障中受影響 82s，最長無回應 0s；restore 期間 0s；全程失敗 33：UPSERT×2/DELETE×1/INSERT×26/SELECT×4）；jdbc 不可用（故障中受影響 133s，最長無回應 0s；restore 期間 0s；全程失敗 52：INSERT×30/SELECT×22）；flight 讀取失敗（故障中受影響 146s，最長無回應 21s；restore 期間 0s；全程失敗 15：SELECT×15）；故障中 alive check failed: OperationalError: (1105, 'Exception, msg: Failed to get master client.')；log `results/pass-2/double-crossed/`
- 實測 第3輪 2026-09-11：mysql 只讀（故障中受影響 107s，最長無回應 0s；restore 期間 0s；全程失敗 57：UPSERT×1/DELETE×2/SELECT×22/INSERT×32）；jdbc 不可用（故障中受影響 133s，最長無回應 9s；restore 期間 0s；全程失敗 63：INSERT×33/SELECT×29/DELETE×1）；flight 讀取失敗（故障中受影響 142s，最長無回應 25s；restore 期間 0s；全程失敗 25：SELECT×25）；故障中 alive check failed: OperationalError: (1105, 'Exception, msg: Failed to get master client.')；log `results/pass-3/double-crossed/`
- 實測 結論：不可用（mysql/jdbc 三輪最差），arrow-flight 讀取失敗；影響（失敗＋卡頓）mysql 82～146s、jdbc 133～148s、flight 142～146s

### Requirement: 恢復與回到可寫
故障移除後，系統 SHALL 自動歸隊：VM start 後 FE 以 follower 追上 edit log、BE 的 DEAD 副本恢復 OK；從雙重故障恢復時，寫入 SHALL 在 FE 存活 ≥ 2 且 BE 存活 ≥ 2 的那一刻起恢復。`restore` MUST 逆轉全部故障並記錄每一步的時間；client 不需任何動作。

#### Scenario: 停機 VM 重新啟動
- **WHEN** 對停機的 VM 執行 `gcloud compute instances start`
- **THEN** 90 秒內 FE/BE `Alive=true`、副本 12 OK，三個 client 期間 0 失敗，資料筆數與停機前的寫入一致
- 實測 第1輪 2026-09-11：restore 到叢集健康 61s，restore 後 healthy=True；log `results/pass-1/vm-stop-3clients/`
- 實測 第2輪 2026-09-11：restore 到叢集健康 49s，restore 後 healthy=True；log `results/pass-2/vm-stop-3clients/`
- 實測 第3輪 2026-09-11：restore 到叢集健康 54s，restore 後 healthy=True；log `results/pass-3/vm-stop-3clients/`

#### Scenario: 逐步恢復雙重故障
- **WHEN** 從「VM 停 + 另一台 BE dead」以 restore 逆序恢復：先 systemctl start 該 BE，再 start 該 VM
- **THEN** BE 回來的那一刻（BE 存活回到 2/3）寫入即恢復，不必等 VM；log 可對應出「寫入恢復」時間點；最終副本 12 OK、資料一致
- 實測 第1輪 2026-09-11：restore 到叢集健康 52s，restore 後 healthy=True；log `results/pass-1/double-vm-be-dead/`
- 實測 第2輪 2026-09-11：restore 到叢集健康 57s，restore 後 healthy=True；log `results/pass-2/double-vm-be-dead/`
- 實測 第3輪 2026-09-11：restore 到叢集健康 52s，restore 後 healthy=True；log `results/pass-3/double-vm-be-dead/`

#### Scenario: crash 後的自動恢復
- **WHEN** crash 方式注入的故障由 systemd 自動拉起程序
- **THEN** 不需 `restore`，60 秒內叢集回到健康；`measure` 的 EVENT 時間軸能看出拉起時間
- 實測 第1輪 2026-09-11：restore 到叢集健康 6s，restore 後 healthy=True；log `results/pass-1/fe-crash-master/`
- 實測 第2輪 2026-09-11：restore 到叢集健康 6s，systemd 拉起 +9s，restore 後 healthy=True；log `results/pass-2/fe-crash-master/`
- 實測 第3輪 2026-09-11：restore 到叢集健康 6s，systemd 拉起 +9s，restore 後 healthy=True；log `results/pass-3/fe-crash-master/`
