#!/usr/bin/env python3
"""Aggregate results/pass-*/<id>/summary.json into results/summary.json and write the 實測 blocks into
openspec/changes/fault-matrix/specs/fault-scenarios/spec.md (after each matching Scenario's THEN line).
Design text is never touched; only lines starting with '- 實測' are (re)written.

  ./venv/bin/python experiments/fill_results.py            # aggregate + fill spec
  ./venv/bin/python experiments/fill_results.py --dry-run  # aggregate only
  ./venv/bin/python experiments/fill_results.py --dry-run --passes=0   # look at a smoke run
"""
import json, pathlib, re, sys, datetime, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cluster   # analyze(log, phase)

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SPEC = ROOT / "openspec/changes/fault-matrix/specs/fault-scenarios/spec.md"
DRY = "--dry-run" in sys.argv
PASSES = next((a.split("=",1)[1] for a in sys.argv if a.startswith("--passes=")), "1,2,3")   # smoke runs (pass-0) are excluded by default
PASSES = {int(x) for x in PASSES.split(",") if x}
RANK = {"rw": 0, "read-ok": 0, "ro": 1, "stalled": 2, "read-stalled": 2, "read-down": 2, "down": 3, "n/a": -1}
ZH = cluster.LEVELS

def ev_secs(events, a_pat, b_pat):
    """seconds between the first event matching a_pat and the first later event matching b_pat"""
    t = lambda l: datetime.datetime.strptime(l[:8], "%H:%M:%S")
    a = next((l for l in events if re.search(a_pat, l)), None); b = next((l for l in events if a and re.search(b_pat, l) and t(l) >= t(a)), None)
    return (t(b) - t(a)).seconds if a and b else None

runs = collections.defaultdict(list)   # id -> [summary per pass]
for f in sorted(RES.glob("pass-*/*/summary.json")):
    s = json.loads(f.read_text(encoding="utf-8"))
    if s["pass"] not in PASSES: continue
    s["_dir"] = str(f.parent.relative_to(ROOT)); runs[s["id"]].append(s)
if not runs: sys.exit("no results yet")

def worst(levels):
    lv = [l for l in levels if l and l != "n/a"]
    return max(lv, key=lambda l: RANK[l]) if lv else "n/a"

agg = {}
for sid, ss in runs.items():
    ss.sort(key=lambda s: s["pass"])
    clients = {}
    for c in ("mysql", "jdbc", "flight"):
        per = []
        for s in ss:
            logf = ROOT / s["_dir"] / f"{c}.log"
            if not logf.exists():
                per.append({"pass": s["pass"], "level": "n/a", "level_zh": "n/a", "impact": None, "failed": None, "failed_by_type": {}, "reconnects": None, "windows": [], "stall": None, "max_gap": None, "after_level": "n/a"}); continue
            d = cluster.analyze(logf, "during"); a = cluster.analyze(logf, "after"); w = cluster.analyze(logf)
            per.append({"pass": s["pass"], "level": d["level"], "level_zh": d["level_zh"],
                        "no_select_evidence": d["window_ops"]["selects_ok"] == 0 and d["window_ops"]["selects_fail"] == 0,
                        "impact": d["impact_secs"], "fail_secs": d["fail_window_secs"], "stall": d["stall_secs"], "max_gap": d["max_gap_secs"],   # fault phase
                        "impact_total": w["impact_secs"], "impact_restore": a["impact_secs"],                                                        # whole log / after restore
                        "failed": w["failed"], "failed_by_type": w["failed_by_type"], "reconnects": w["reconnects"],
                        "windows": w["windows"], "after_level": a["level"]})
        clients[c] = {"passes": per}
    # a write client that only proved "writes fail" (cycle restarts at INSERT, no SELECT evidence; pass 1 had no read check)
    # is read as 只讀 when the read-only client kept reading fine in the same run
    for c in ("mysql", "jdbc"):
        for i, cp in enumerate(clients[c]["passes"]):
            if cp["level"] == "down" and cp.get("no_select_evidence") and clients["flight"]["passes"][i]["level"] == "read-ok":
                cp["level"] = "ro"; cp["level_zh"] = ZH["ro"] + "（由 flight 推斷）"
    for c in ("mysql", "jdbc", "flight"):
        per = clients[c]["passes"]
        clients[c].update({"worst": worst([p["level"] for p in per]), "worst_zh": ZH[worst([p["level"] for p in per])],
                      "impact_min": min((p["impact"] for p in per if p["impact"] is not None), default=None),
                      "impact_max": max((p["impact"] for p in per if p["impact"] is not None), default=None)})
    recov = []
    for s in ss:
        logf = ROOT / s["_dir"] / "mysql.log"
        evs = cluster.analyze(logf)["events"] if logf.exists() else []
        recov.append({"pass": s["pass"], "restore_secs": ev_secs(evs, r"restore: (start|systemctl|resume|verify)", r"restore: cluster healthy"),
                      "systemd_secs": next((int(m.group(1)) for l in evs for m in [re.search(r"restarted by systemd.*\+(\d+)s", l)] if m), None),
                      "healthy_after": s.get("healthy_after"), "alive_during": s.get("alive_during")})
    # overall = worst of the write clients; a write client that only proved "writes fail" (no SELECT evidence, e.g. the
    # cycle restarts at INSERT) is read as 只讀 when the read-only client kept reading fine in the same run
    per_pass_overall = []
    for i in range(len(ss)):
        per_pass_overall.append(worst([clients[c]["passes"][i]["level"] for c in ("mysql", "jdbc")]))
    agg[sid] = {"scenario": ss[0]["scenario"], "also": ss[0].get("also", []), "steps": ss[0]["steps"], "order": ss[0].get("order"),
                "passes": [s["pass"] for s in ss], "dirs": [s["_dir"] for s in ss], "clients": clients, "recovery": recov,
                "overall_per_pass": per_pass_overall, "overall": worst(per_pass_overall)}
(RES / "summary.json").write_text(json.dumps(agg, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"aggregated {len(agg)} scenarios from {sum(len(v) for v in runs.values())} runs -> results/summary.json")
for sid, a in agg.items():
    print(f"  {sid:26} {ZH[a['overall']]:5}  " + "  ".join(f"{c}:{a['clients'][c]['worst_zh']}({a['clients'][c]['impact_min']}~{a['clients'][c]['impact_max']}s)" for c in ("mysql", "jdbc", "flight")))
if DRY: sys.exit(0)

def block_for(sid, title):
    """實測 lines for a Scenario title (main scenario or an `also` recovery scenario)."""
    a = agg[sid]; today = datetime.date.today().isoformat(); lines = []
    if title == a["scenario"]:
        for i, p in enumerate(a["passes"]):
            parts = []
            for c in ("mysql", "jdbc", "flight"):
                cp = a["clients"][c]["passes"][i]
                parts.append(f"{c} {cp['level_zh']}（故障中受影響 {cp['impact']}s，最長無回應 {cp['max_gap']}s；restore 期間 {cp['impact_restore']}s；全程失敗 {cp['failed']}{'：' + '/'.join(f'{k}×{v}' for k, v in (cp['failed_by_type'] or {}).items()) if cp['failed_by_type'] else ''}）")
            lines.append(f"- 實測 第{p}輪 {today}：" + "；".join(parts) + f"；故障中 {a['recovery'][i]['alive_during']}；log `{a['dirs'][i]}/`")
        lines.append(f"- 實測 結論：{ZH[a['overall']]}（mysql/jdbc 三輪最差），arrow-flight {a['clients']['flight']['worst_zh']}；影響（失敗＋卡頓）mysql {a['clients']['mysql']['impact_min']}～{a['clients']['mysql']['impact_max']}s、jdbc {a['clients']['jdbc']['impact_min']}～{a['clients']['jdbc']['impact_max']}s、flight {a['clients']['flight']['impact_min']}～{a['clients']['flight']['impact_max']}s")
    else:   # recovery scenarios reuse the restore timing of the main scenario
        for i, p in enumerate(a["passes"]):
            r = a["recovery"][i]
            lines.append(f"- 實測 第{p}輪 {today}：restore 到叢集健康 {r['restore_secs']}s" + (f"，systemd 拉起 +{r['systemd_secs']}s" if r["systemd_secs"] is not None else "") + f"，restore 後 healthy={r['healthy_after']}；log `{a['dirs'][i]}/`")
    return lines

text = SPEC.read_text(encoding="utf-8")
title_to_sid = {}
for sid, a in agg.items():
    title_to_sid[a["scenario"]] = sid
    for t in a["also"]: title_to_sid.setdefault(t, sid)
out = []; cur = None; filled = 0
for line in text.splitlines():
    m = re.match(r"^#### Scenario:\s*(.+)$", line)
    if m:
        cur = m.group(1).strip(); out.append(line); continue
    if line.startswith("- 實測"): continue          # drop old measured lines; rewritten below
    if cur and (line.startswith("### ") or line.startswith("#### ") or line.startswith("## ")):
        cur = None
    out.append(line)
# insert after the THEN line of each filled scenario
res = []; cur = None; pending = None
for line in out:
    m = re.match(r"^#### Scenario:\s*(.+)$", line)
    if m: cur = m.group(1).strip(); pending = title_to_sid.get(cur)
    res.append(line)
    if pending and line.startswith("- **THEN**"):
        res.extend(block_for(pending, cur)); filled += 1; pending = None
SPEC.write_text("\n".join(res) + "\n", encoding="utf-8")
print(f"filled 實測 blocks for {filled} scenario(s) in {SPEC.relative_to(ROOT)}")
