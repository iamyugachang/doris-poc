# fault-scenarios Specification

## Purpose
故障矩陣：每個情境的注入方式、預期的可用性等級（讀寫正常 / 只讀 / 不可用）與觀察點。這裡只寫假設；實測見 results/ 與 results.html。

## Requirements

### Requirement: 可用性等級
結果 SHALL 以三個等級之一描述：**讀寫正常**（中斷視窗後全部操作恢復）、**只讀**（SELECT 可用、寫入持續失敗）、**不可用**（SELECT 也失敗）。等級由 FE 與 BE 各自的多數決推導：任一層存活 < 2 ⇒ 寫入不可用。

#### Scenario: 等級判定
- **WHEN** 故障注入後觀察至少 60 秒
- **THEN** 依最後 30 秒（或最後一個 EVENT 之後）的成功率判定等級，並記錄中斷秒數與失敗數

#### Scenario: 每格三輪
- **WHEN** 執行矩陣
- **THEN** 每格跑三個獨立輪次（每輪從全部 VM 開機開始），等級取三輪最差

### Requirement: 單一 VM 停機
一台 VM 整台停機時，系統 SHALL 維持**讀寫正常**：FE 剩 2/3 可選主，BE 剩 2/3 可寫。

#### Scenario: master 所在 VM 停機，client 直連 master
- **WHEN** client 連在 master FE，該 VM 被 stop
- **THEN** client 換台後 5 秒內恢復，寫入失敗 ≤ 2 次；等級：讀寫正常

#### Scenario: master 所在 VM 停機，client 連在 follower
- **WHEN** client 連在 follower FE，master 所在 VM 被 stop
- **THEN** 寫入因轉發給已消失的 master 而失敗，選主後恢復；觀察：client 是否因等逾時而拉長中斷；等級：讀寫正常

#### Scenario: follower 所在 VM 停機
- **WHEN** 非 master 的 VM 被 stop
- **THEN** master 不變，只有連在該 FE 的 client 重連；副本 8 OK / 4 DEAD；等級：讀寫正常

#### Scenario: 三個 client 同時觀察 VM 停機
- **WHEN** mysql / jdbc / arrow-flight 同時運行，master 所在 VM 被 stop
- **THEN** 三者皆 5 秒內恢復（arrow-flight 只驗讀取），三份 log 可互相對照；等級：讀寫正常

### Requirement: FE 程序故障
單一 FE crash、dead 或 hang 而 VM 與 BE 正常時，系統 SHALL 維持**讀寫正常**；影響範圍取決於它是否為 master、client 是否連在它上面。

#### Scenario: master FE crash（kill -9，systemd 自動拉起）
- **WHEN** master FE 被 kill -9，systemd 10 秒內拉起
- **THEN** 剩餘 2 個 FE 選出新 master；連在它上的 client 重連；拉起後以 follower 歸隊；等級：讀寫正常

#### Scenario: follower FE crash
- **WHEN** 某 follower FE 被 kill -9
- **THEN** 只有連在它上的 client 重連，master 不變；等級：讀寫正常

#### Scenario: master FE dead（systemctl stop，不自動起）
- **WHEN** master FE 被 systemctl stop
- **THEN** 選出新 master，叢集以 2 個 FE 運作、FE 層無冗餘；等級：讀寫正常

#### Scenario: master FE hang（kill -STOP）
- **WHEN** master FE 被暫停（活著但不回應）
- **THEN** 連在它上的 client 等到 8 秒逾時才換台；其他 FE 心跳逾時後重新選主；觀察：中斷是否明顯長於 crash；等級：讀寫正常

#### Scenario: follower FE hang
- **WHEN** 某 follower FE 被暫停
- **THEN** 連在它上的 client 逾時後換台，其他 client 無感；等級：讀寫正常

### Requirement: BE 程序故障
單一 BE crash、dead 或 hang 而 FE 正常時，系統 SHALL 維持**讀寫正常**（副本 2/3）。

#### Scenario: BE crash（systemd 自動拉起）
- **WHEN** 某 BE 被 kill -9，systemd 10 秒內拉起
- **THEN** 可能 1 次操作逾時；副本短暫 DEAD 後恢復 OK；等級：讀寫正常

#### Scenario: BE dead
- **WHEN** 某 BE 被 systemctl stop
- **THEN** 副本 8 OK / 4 DEAD，寫入以 2/3 副本成功；等級：讀寫正常（降級）

#### Scenario: BE hang（kill -STOP）
- **WHEN** 某 BE 被暫停
- **THEN** 落在該 BE 的操作等到逾時才失敗，FE 心跳逾時後標 DEAD 並改派副本；觀察：中斷是否長於 dead；等級：讀寫正常

### Requirement: 雙重故障
兩個元件同時故障時，等級 SHALL 依兩層各自的多數決推導；SELECT 在任一 FE 可服務且 BE ≥ 1 時 MAY 仍可用，是否真的可用由實驗決定。

#### Scenario: VM 停 + 另一台 FE dead（FE 剩 1/3）
- **WHEN** master 所在 VM 停機後，再 systemctl stop 剩餘 2 個 FE 之一
- **THEN** 無法選主，寫入全部失敗；觀察：SELECT 是否可用；等級：只讀或不可用

#### Scenario: VM 停 + 另一台 BE dead（BE 剩 1/3）
- **WHEN** 一台 VM 停機後，再 systemctl stop 剩餘 2 個 BE 之一
- **THEN** 寫入湊不到 2/3 副本而失敗，SELECT 由僅存副本服務；等級：只讀

#### Scenario: 兩台 VM 停（FE 1/3、BE 1/3）
- **WHEN** 兩台 VM 先後停機
- **THEN** 寫入失敗；觀察：SELECT 是否可用；等級：只讀或不可用

#### Scenario: 交錯故障（一台 VM 停、一台 BE dead、一台 FE dead）
- **WHEN** doris-1 VM 停、doris-2 BE stop、doris-3 FE stop
- **THEN** FE 與 BE 各剩 1/3，驗證「等級由兩層各自的多數決決定」；等級：只讀或不可用

### Requirement: 恢復與回到可寫
故障移除後，系統 SHALL 自動歸隊；從雙重故障恢復時，寫入 SHALL 在 FE ≥ 2 且 BE ≥ 2 的那一刻恢復。`restore` MUST 逆轉全部故障並記錄每步時間；client 不需任何動作。

#### Scenario: 停機 VM 重新啟動
- **WHEN** 對停機的 VM 執行 start
- **THEN** 90 秒內 FE/BE `Alive=true`、副本 12 OK，client 0 失敗，資料筆數一致

#### Scenario: 逐步恢復雙重故障
- **WHEN** 從「VM 停 + 另一台 BE dead」逆序恢復：先 start 該 BE，再 start VM
- **THEN** BE 回來的那一刻寫入即恢復，不必等 VM；最終副本 12 OK、資料一致

#### Scenario: crash 後的自動恢復
- **WHEN** crash 方式的故障由 systemd 自動拉起
- **THEN** 不需 `restore`，60 秒內叢集回到健康；EVENT 時間軸能看出拉起時間
