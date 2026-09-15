## Why

Doris 三節點（每台 FE + BE）在各種故障下，client 是「照常」、「只能查」還是「不能用」？恢復要多久？目前只有 quorum 推論，沒有數據。本 change 把故障情境排成矩陣，用同一套 client 與量測跑每一格。

## What Changes

- 新增 `fault-scenarios` 規格：可用性等級定義、每個故障情境的預期
  - 對象：FE / BE / 整台 VM；方式：crash / dead / hang / stop；位置：master 所在 / follower 所在
  - 雙重故障：VM 停 + FE dead、VM 停 + BE dead、兩台 VM 停、交錯
- `break` 支援 對象 / 方式 / 位置，可疊加；`restore` 逆序逆轉全部
- `measure` 加上可用性等級判定
- 矩陣執行器逐格跑 3 輪，結果存 results/；網站三頁：specs.html（設計）→ results.html（結果）→ index.html（結論）
- 拓撲、client 協定、探測循環不變

## Non-goals

- 網路分割、zone 級故障
- 效能影響、小時級長故障
- 修改 Doris 參數縮短恢復時間

## Capabilities

### New Capabilities
- `fault-scenarios`：可用性等級定義、單一 VM 停機、FE 程序故障、BE 程序故障、雙重故障、恢復

### Modified Capabilities
- `operations`：`break` 可指定對象 / 方式 / 位置並疊加；`restore` 逆轉全部；`measure` 輸出可用性等級

## Impact

- `demo.sh`、`cluster.py`：break / restore / measure 參數、狀態檔、位置解析、等級判定
- client VM 與探測程式：不變
- 成本：16 格 × 3 輪，每格約 4 分鐘，VM 約 4 小時（US$2～3）
