## 1. 故障注入工具

- [x] 1.1 `cluster.py`：新增位置解析 `master` / `follower` / 指定 VM，以及 BE 所在對應；驗證 `cluster.py master|follower <hosts>` 各印出正確 VM 名
- [x] 1.2 `demo.sh break`：支援 `--target fe|be|vm --mode crash|dead|hang|stop --on master|follower|<vm>`，注入後寫入三份 log 的 EVENT 行並追加 `.state/faults`；驗證 `break --dry-run` 印出正確的 gcloud/ssh 指令，且不帶參數時行為與 operations spec 的「停掉 master 所在 VM」一致
- [x] 1.3 `demo.sh break --mode crash`：注入後輪詢 systemd `ActiveEnterTimestamp`，拉起時寫入 `EVENT recovered …`；驗證 log 出現該行且時間差約 10 秒
- [x] 1.4 `demo.sh restore`：逆序逆轉 `.state/faults` 全部項目（VM start / systemctl start / kill -CONT），逐步寫 EVENT，最後等待健康並清空狀態檔；驗證疊加兩個故障後一次 restore 回到健康
- [x] 1.5 `demo.sh status`：顯示 `.state/faults` 內容與 FE/BE 存活數（例如 FE 2/3、BE 3/3）；驗證輸出

## 2. 量測

- [x] 2.1 `cluster.py measure`：新增可用性等級判定（讀寫正常 / 只讀 / 不可用，arrow-flight 只判讀取）與判定窗口；驗證用一段健康期間的 log 判為讀寫正常、用人工造的「寫入全失敗」log 判為只讀
- [x] 2.2 `demo.sh measure --label <情境>`：輸出每個 client 的等級一行摘要，並把三份 log 複製到 `logs/<日期>-<情境>-<client>.log`；驗證檔案落地

- [x] 2.3 `experiments/scenarios.yaml` + `experiments/run_matrix.py --pass N`：逐格 monitor → baseline → break 序列 → 觀察 → restore → 等健康 → measure，結果寫 `results/pass-N/<id>/`；驗證用單一格 `--only vm-stop-master` 端到端跑通
- [x] 2.4 `experiments/fill_results.py`：彙整 results/ 三輪 → 回填 delta spec 各 Scenario 的「實測」段落、產生 `site/results.html` 與 index.html 矩陣表；驗證用試跑結果產出一次

## 3. 單一 VM 停機實驗（每格由執行器跑 3 輪；結果由 fill_results 回填 fault-scenarios spec 對應 Scenario）

- [x] 3.1 `break`（master 所在 VM stop），觀察三個 client → 回填「三個 client 同時觀察 VM 停機」
- [x] 3.2 同 3.1 但事先讓 mysql client 連在 master（調整 hosts 順序）→ 回填「master 所在 VM 停機，client 直連 master」
- [x] 3.3 同 3.1 但 mysql client 連在 follower → 回填「master 所在 VM 停機，client 連在 follower」
- [x] 3.4 `break --on follower` → 回填「follower 所在 VM 停機」
- [x] 3.5 對 3.1 的 restore 記錄 start 到副本 12 OK 的秒數與資料筆數 → 回填「停機 VM 重新啟動」

## 4. FE / BE 程序故障實驗（同上，3 輪）

- [x] 4.1 `break --target fe --mode crash --on master` → 回填「master FE crash」
- [x] 4.2 `break --target fe --mode crash --on follower` → 回填「follower FE crash」
- [x] 4.3 `break --target fe --mode dead --on master` → 回填「master FE dead」
- [x] 4.4 `break --target fe --mode hang --on master` → 回填「master FE hang」，並把 FE 判定失聯的秒數回填 design.md Open Questions
- [x] 4.5 `break --target fe --mode hang --on follower` → 回填「follower FE hang」
- [x] 4.6 `break --target be --mode crash` → 回填「BE crash」
- [x] 4.7 `break --target be --mode dead` → 回填「BE dead」
- [x] 4.8 `break --target be --mode hang` → 回填「BE hang」
- [x] 4.9 對 4.1 與 4.6 記錄 systemd 拉起到叢集健康的秒數 → 回填「crash 後的自動恢復」

## 5. 雙重故障實驗（同上，3 輪；兩次 break 之間觀察 ≥ 30s）

- [x] 5.1 `break`（VM stop）+ `break --target fe --mode dead --on follower` → 回填「VM 停 + 另一台 FE dead」，並把 SELECT 是否可用回填 design.md Open Questions
- [x] 5.2 `break`（VM stop）+ `break --target be --mode dead --on follower` → 回填「VM 停 + 另一台 BE dead」
- [x] 5.3 `break` + `break --target vm --on follower` → 回填「兩台 VM 停」
- [x] 5.4 `break --on doris-1` + `break --target be --mode dead --on doris-2` + `break --target fe --mode dead --on doris-3` → 回填「交錯故障」
- [x] 5.5 對 5.2 記錄第二個元件恢復後多久回到可寫 → 回填「逐步恢復雙重故障」

## 6. 報告與收尾

- [x] 6.1 `site/results.html`（過程與全部結果：每格三輪、每個 client、EVENT 時間軸、log 連結）與 `site/index.html` 精簡矩陣章節，重新部署 Cloud Run；驗證線上三頁互相連結
- [x] 6.2 `site/build_specs.py` 重跑產生 `specs.html`（含所有實測段落）並部署；驗證線上規格頁每個 Scenario 都有綠底實測
- [ ] 6.3 README：更新 break/restore/measure 的參數說明與矩陣結果摘要
- [ ] 6.4 `openspec validate fault-matrix --strict` 通過、所有 Scenario 都有「實測」段落後執行 archive 同步主 spec
