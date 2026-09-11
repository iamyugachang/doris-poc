## Why

我們要知道：Doris 三節點（每台 FE + BE）在各種故障下，client 的讀寫到底是「照常」、「只能查」還是「整個不能用」，以及恢復要多久。目前只有 quorum 規則的推論，沒有數據。本 change 把故障情境設計成一個矩陣，用同一套 client 與量測跑過每一格，把結果記成 spec，讓其他人不必重做也能知道這個架構的邊界。

## What Changes

- 新增 `fault-scenarios` 規格：可用性等級的定義、故障矩陣的每個情境與預期
  - 對象：FE 程序 / BE 程序 / 整台 VM
  - 方式：crash（kill -9，systemd 自動拉起）/ dead（systemctl stop，等人工恢復）/ hang（kill -STOP，程序活著但不回應）/ stop（VM 停機）
  - 位置：master 所在 / follower 所在
  - 雙重故障：VM 停 + 另一台 FE dead、VM 停 + 另一台 BE dead、兩台 VM 停、交錯（一台 VM 停、一台只死 BE、一台只死 FE）
  - 恢復：VM start、程序 restart、雙重故障的逐步恢復
- `break` 支援指定對象 / 方式 / 位置，可連續執行以疊加故障；`restore` 依相反順序逆轉全部故障
- `measure` 在原有中斷視窗之外，對每個 client 判定可用性等級
- 用矩陣執行器自動逐格跑完整個矩陣，每個 Scenario 跑 3 輪（一輪 = 全部 VM 開機 → 跑完矩陣 → 全部關機），結果存 results/ 並由工具回填到每個 Scenario 的「實測」段落
- 網站三頁對應 demo 順序：specs.html（實驗設計）→ results.html（過程與全部結果）→ index.html（精簡矩陣與結論）
- 不改變拓撲、client 協定與探測循環

## Non-goals

- 網路分割（iptables 斷開特定節點之間的流量）與 zone 級故障：留到下一個 change
- 效能影響、長時間（小時級）故障
- 修改 Doris 參數（例如 FE 心跳、選主逾時）來縮短恢復時間

## Capabilities

### New Capabilities
- `fault-scenarios`：可用性等級定義、單一 VM 停機、FE 程序故障、BE 程序故障、雙重故障、恢復與回到可寫

### Modified Capabilities
- `operations`：`break` 從「停 master 所在 VM」擴充為可指定對象/方式/位置並可疊加；`restore` 逆轉全部；`measure` 輸出可用性等級

## Impact

- `demo.sh`：break / restore / measure 的參數與狀態檔（一次記多個故障）
- `cluster.py`：master / follower / BE 位置查詢、可用性等級判定
- client VM 與探測程式：不變（hang 情境會讓探測等到 8 秒逾時，屬預期）
- Doris 節點：`dead` 方式依賴 `systemctl stop` 不觸發自動重啟；`crash` 依賴 `Restart=on-failure`（RestartSec=10）
- `site/`：新增故障矩陣章節與各格結果；`site/specs.html` 由 openspec/ 重新產生
- 實驗約 20 格 × 3 輪，每格 3～5 分鐘，VM 運行約 4 小時（約 US$2～3）；雙重故障情境預期出現寫入失敗，屬實驗設計的一部分
