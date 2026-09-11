#!/usr/bin/env python3
"""Cluster-side helpers for demo.sh (needs pymysql). All commands read hosts.tsv
(name<TAB>zone<TAB>internal_ip<TAB>external_ip) written by demo.sh.

  cluster.py status   <hosts.tsv>                 one-page FE/BE/replica view
  cluster.py master   <hosts.tsv>                 print VM name of current FE master
  cluster.py wait     <hosts.tsv> <sec>           block until every FE/BE alive and all replicas OK
  cluster.py seed     <hosts.tsv> <rows>          create hatest.events (3 replicas) + seed rows if empty
  cluster.py probe    <hosts.tsv> <sec> <log>     1 op/s cycling INSERT>UPSERT>SELECT>DELETE>SELECT with FE failover
  cluster.py measure  <log> [--json]               outage windows / failure counts / availability level from a probe log
  cluster.py report   <state-dir> <hosts.tsv>      one-line JSON for all three probe logs + alive + faults
  cluster.py resolve  <hosts.tsv> master|follower|<vm>   print the VM name for a --on value
  cluster.py role     <hosts.tsv> <vm>             print "FE master" / "FE follower" / "FE down"
  cluster.py alive    <hosts.tsv>                  one-line FE/BE alive counts (tolerates a dead cluster)
"""
import sys, time, datetime, re, collections
import pymysql

DB, TABLE = "hatest", "events"

def hosts(path):
    out = []
    for line in open(path):
        if line.strip():
            n, z, i, e = line.rstrip("\n").split("\t")
            out.append({"name": n, "zone": z, "int": i, "ext": e})
    return out

def connect(hs, db=None, timeout=3):
    last = None
    for h in hs:
        if not h["ext"]:
            continue
        try:
            return h, pymysql.connect(host=h["ext"], port=9030, user="root", password="", database=db,
                                      connect_timeout=timeout, read_timeout=6, write_timeout=6, autocommit=True)
        except Exception as e:
            last = e
    raise SystemExit(f"no FE reachable: {last}")

def rows(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def snapshot(hs):
    via, c = connect(hs)
    with c.cursor() as cur:
        fes = rows(cur, "SHOW FRONTENDS")
        bes = rows(cur, "SHOW BACKENDS")
        try:
            reps = rows(cur, f"ADMIN SHOW REPLICA STATUS FROM {DB}.{TABLE}")
            cur.execute(f"SELECT count(*) FROM {DB}.{TABLE}"); cnt = cur.fetchone()[0]
        except Exception:
            reps, cnt = [], None
    c.close()
    return via, fes, bes, reps, cnt

def name_of(hs, ip):
    return next((h["name"] for h in hs if h["int"] == ip), ip)

def cmd_status(hs):
    via, fes, bes, reps, cnt = snapshot(hs)
    print(f"(queried via {via['name']} {via['ext']})")
    print("FE:")
    for f in sorted(fes, key=lambda x: x["Host"]):
        tag = "MASTER" if f["IsMaster"] == "true" else "follower"
        print(f"  {name_of(hs, f['Host']):8} {f['Host']:12} {tag:8} alive={f['Alive']:5} journal={f['ReplayedJournalId']}")
    print("BE:")
    for b in sorted(bes, key=lambda x: x["Host"]):
        print(f"  {name_of(hs, b['Host']):8} {b['Host']:12} alive={b['Alive']:5} tablets={b['TabletNum']}")
    st = collections.Counter(r["Status"] for r in reps)
    print(f"replicas {DB}.{TABLE}: {dict(st) or 'n/a'}   rows={cnt}")

def cmd_master(hs):
    _, fes, *_ = snapshot(hs)
    m = next((f for f in fes if f["IsMaster"] == "true"), None)
    if not m:
        raise SystemExit("no master elected yet")
    print(name_of(hs, m["Host"]))

def cmd_resolve(hs, on):
    """Print the VM name for --on master|follower|<vm-name>."""
    names = [h["name"] for h in hs]
    if on in names: print(on); return
    _, fes, *_ = snapshot(hs)
    master = next((name_of(hs, f["Host"]) for f in fes if f["IsMaster"] == "true"), None)
    if on == "master":
        if not master: raise SystemExit("no master elected")
        print(master); return
    if on == "follower":
        alive = [name_of(hs, f["Host"]) for f in sorted(fes, key=lambda x: x["Host"]) if f["Alive"] == "true" and f["IsMaster"] != "true"]
        if not alive: raise SystemExit("no alive follower")
        print(alive[0]); return
    raise SystemExit(f"unknown --on value: {on}")

def cmd_role(hs, vm):
    """Print 'FE master' / 'FE follower' / 'FE down' for a VM (used in EVENT lines)."""
    try:
        _, fes, *_ = snapshot(hs)
    except SystemExit:
        print("FE unknown"); return
    f = next((f for f in fes if name_of(hs, f["Host"]) == vm), None)
    print("FE unknown" if not f else "FE master" if f["IsMaster"] == "true" else "FE follower" if f["Alive"] == "true" else "FE down")

def cmd_alive(hs):
    """One line: FE a/3 (master X) BE b/3 replicas {...}; tolerant when no FE is reachable."""
    try:
        via, fes, bes, reps, cnt = snapshot(hs)
    except SystemExit as e:
        print(f"FE 0/{len(hs)}? BE ?/{len(hs)} (no FE reachable: {e})"); return
    fe_alive = sum(1 for f in fes if f["Alive"] == "true"); be_alive = sum(1 for b in bes if b["Alive"] == "true")
    master = next((name_of(hs, f["Host"]) for f in fes if f["IsMaster"] == "true"), "none")
    st = collections.Counter(r["Status"] for r in reps)
    print(f"FE {fe_alive}/{len(hs)} (master {master}) BE {be_alive}/{len(hs)} replicas {dict(st) or 'n/a'} rows={cnt} via {via['name']}")

def healthy(hs):
    try:
        _, fes, bes, reps, _ = snapshot(hs)
    except BaseException as e:            # unreachable FE, no master yet, catalog not ready … all mean "not healthy yet"
        return False, f"{type(e).__name__}: {str(e)[:90]}"
    bad = [name_of(hs, f["Host"]) + "(fe)" for f in fes if f["Alive"] != "true" or f["Join"] != "true"]
    bad += [name_of(hs, b["Host"]) + "(be)" for b in bes if b["Alive"] != "true"]
    st = collections.Counter(r["Status"] for r in reps)
    if reps and set(st) != {"OK"}:
        bad.append(f"replicas={dict(st)}")
    return (len(fes) == len(hs) and len(bes) == len(hs) and not bad), (", ".join(bad) or f"fe={len(fes)} be={len(bes)}")

def cmd_wait(hs, sec):
    t0 = time.time()
    while True:
        ok, why = healthy(hs)
        if ok:
            print(f"healthy after {int(time.time()-t0)}s"); return
        if time.time() - t0 > sec:
            raise SystemExit(f"NOT healthy after {sec}s: {why}")
        print(f"  waiting ({int(time.time()-t0)}s): {why}", flush=True)
        time.sleep(5)

def cmd_seed(hs, n):
    _, c = connect(hs)
    with c.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB}")
        cur.execute(f"SHOW TABLES FROM {DB} LIKE '{TABLE}'")
        if cur.fetchone():
            cur.execute(f"SHOW CREATE TABLE {DB}.{TABLE}")
            if "UNIQUE KEY" not in cur.fetchone()[1]:
                print(f"  {DB}.{TABLE} is not a UNIQUE KEY table — recreating for upsert/delete probe")
                cur.execute(f"DROP TABLE {DB}.{TABLE}")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {DB}.{TABLE} (id BIGINT, ts DATETIME, msg VARCHAR(64), ver INT)
                        UNIQUE KEY(id) DISTRIBUTED BY HASH(id) BUCKETS 4
                        PROPERTIES ("replication_num"="3", "enable_unique_key_merge_on_write"="true")""")
        cur.execute(f"SELECT count(*) FROM {DB}.{TABLE}"); cnt = cur.fetchone()[0]
        if cnt == 0:
            cur.execute(f'INSERT INTO {DB}.{TABLE} SELECT number, now(), "seed", 1 FROM numbers("number"="{n}")')
            cur.execute(f"SELECT count(*) FROM {DB}.{TABLE}"); cnt = cur.fetchone()[0]
    c.close()
    print(f"{DB}.{TABLE} (UNIQUE KEY, 3 replicas) rows={cnt}")

OPS = ("INSERT", "UPSERT", "SELECT", "DELETE", "SELECT")   # one full round = one key's life cycle

def cmd_probe(hs, sec, logpath):
    """Every second run the next op of the cycle on key k (k advances each round):
       INSERT (id=k, ver=1) -> UPSERT (same id, ver=2) -> SELECT (expect ver=2)
       -> DELETE (id=k) -> SELECT (expect gone). A failed op is logged with its type; the key is retried
       from INSERT on the next round so the cycle stays consistent."""
    log = open(logpath, "a")
    def out(msg):
        line = f"{datetime.datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True); log.write(line + "\n"); log.flush()
    conn = via = None; just_failed = False; i = ok = fail = reconnects = 0
    per_op = collections.Counter(); per_op_fail = collections.Counter()
    t0 = time.time(); k = 1_000_000 + (int(t0) % 100_000) * 10; step = 0
    out(f"PROBE start hosts={','.join(h['name'] for h in hs)} duration={sec}s cycle={'>'.join(OPS)}")
    while time.time() - t0 < sec:
        i += 1; op = OPS[step]
        try:
            if conn is None:
                via, conn = connect(hs, DB); reconnects += 1
                out(f"connected to {via['name']} ({via['ext']})")
            with conn.cursor() as c:
                if op == "INSERT":
                    c.execute(f"INSERT INTO {TABLE} VALUES ({k}, now(), 'probe', 1)")
                elif op == "UPSERT":
                    c.execute(f"INSERT INTO {TABLE} VALUES ({k}, now(), 'probe-updated', 2)")
                elif op == "DELETE":
                    c.execute(f"DELETE FROM {TABLE} WHERE id = {k}")
                else:  # SELECT verifies the previous write on the same key
                    c.execute(f"SELECT ver FROM {TABLE} WHERE id = {k}"); r = c.fetchone()
                    want = 2 if step == 2 else None
                    got = r[0] if r else None
                    if got != want:
                        raise RuntimeError(f"verify id={k}: want ver={want} got {got}")
                c.execute(f"SELECT count(*) FROM {TABLE}"); cnt = c.fetchone()[0]
                fes = rows(c, "SHOW FRONTENDS")
            ok += 1; per_op[op] += 1
            fe_s = " ".join(f"{name_of(hs, f['Host'])}:{'M' if f['IsMaster']=='true' else 'f'}:{'up' if f['Alive']=='true' else 'DOWN'}"
                            for f in sorted(fes, key=lambda x: x["Host"]))
            out(f"#{i} OK {op:6} id={k} via {via['name']} rows={cnt} [{fe_s}]" + (" (recovered)" if just_failed else ""))
            just_failed = False
            step += 1
            if step == len(OPS): step = 0; k += 1
        except Exception as e:
            fail += 1; per_op_fail[op] += 1; just_failed = True
            out(f"#{i} FAIL {op:6} id={k} via {via['name'] if via else '-'}: {type(e).__name__}: {str(e)[:100]}")
            try: conn.close()
            except Exception: pass
            conn = None
            step = 0; k += 1          # restart the cycle on a fresh key
        time.sleep(1)
    ops_s = " ".join(f"{o}={per_op[o]}/{per_op[o]+per_op_fail[o]}" for o in dict.fromkeys(OPS))
    out(f"PROBE end ok={ok} fail={fail} reconnects={reconnects} per-op(ok/total) {ops_s}")

LEVELS = {"rw": "讀寫正常", "ro": "只讀", "down": "不可用", "stalled": "卡住（無回應）",
          "read-ok": "讀取正常", "read-down": "讀取失敗", "read-stalled": "讀取卡住", "n/a": "n/a"}
GAP = 5   # seconds between consecutive probe lines above which the client is considered stalled

def analyze(logpath, phase=None):
    """Parse one probe log. phase: None = whole log; 'during' = from the last 'EVENT break' to the first
    'EVENT restore' (fault active); 'after' = after 'EVENT restore: cluster healthy'.
    Impact = failure windows (first FAIL -> next OK) + stalls (gaps > GAP s between consecutive lines)."""
    lines = open(logpath, encoding="utf-8", errors="replace").read().splitlines()
    ts = lambda l: datetime.datetime.strptime(l[:8], "%H:%M:%S")
    is_ok = lambda l: re.search(r"#\d+ OK ", l) is not None
    is_fail = lambda l: " FAIL " in l
    is_op = lambda l: is_ok(l) or is_fail(l)
    op_of = lambda l: (re.search(r"#\d+ (?:OK|FAIL) (\w+)", l) or [None, None])[1]
    events = [l for l in lines if " EVENT " in l]
    read_only_client = any("SELECT-only mode" in l for l in lines)
    # ---- phase window
    t_from = t_to = None
    if phase == "during":
        b = [l for l in events if "EVENT break" in l]; r = [l for l in events if "EVENT restore" in l]
        if b: t_from = ts(b[0])
        if r: t_to = ts(r[0])
    elif phase == "after":
        h = [l for l in events if "restore: cluster healthy" in l]
        if h: t_from = ts(h[-1])
    def inside(l):
        t = ts(l); return (t_from is None or t >= t_from) and (t_to is None or t <= t_to)
    body = [l for l in lines if (is_op(l) or "PROBE start" in l or " EVENT " in l) and inside(l)]
    ops = [l for l in body if is_op(l)]
    fails = [l for l in ops if is_fail(l)]
    recon = [l for l in lines if "connected to" in l and inside(l)]
    # ---- failure windows: FAIL -> next OK (may extend past the window end)
    windows = []; i = 0; all_ops = [l for l in lines if is_op(l)]
    idx = {id(l): k for k, l in enumerate(all_ops)}
    k = 0
    while k < len(all_ops):
        l = all_ops[k]
        if is_fail(l) and inside(l):
            j = k
            while j < len(all_ops) and not is_ok(all_ops[j]): j += 1
            end = ts(all_ops[j]) if j < len(all_ops) else None
            windows.append({"start": l[:8], "end": all_ops[j][:8] if end else None, "secs": (end - ts(l)).seconds if end else None})
            k = j
        k += 1
    # ---- stalls: gaps > GAP between consecutive probe lines over the WHOLE log, clipped to the phase window
    allseq = sorted([l for l in lines if is_op(l) or "PROBE start" in l], key=ts); gaps = []   # EVENT lines excluded: they are not client activity
    for a, b in zip(allseq, allseq[1:]):
        if not is_op(b): continue
        ga, gb = ts(a), ts(b)
        if (gb - ga).seconds <= GAP: continue
        lo = max(ga, t_from) if t_from else ga; hi = min(gb, t_to) if t_to else gb
        if hi > lo: gaps.append({"from": a[:8], "to": b[:8], "secs": (hi - lo).seconds})
    stall = sum(g["secs"] for g in gaps); max_gap = max((g["secs"] for g in gaps), default=0)
    # ---- availability level over the phase window (or the last 30 ops when no phase)
    win = ops if phase else ops[-30:]
    seq = sorted(body, key=ts)
    span = (ts(seq[-1]) - ts(seq[0])).seconds if len(seq) > 1 else 0
    if phase == "during" and t_from and t_to: span = (t_to - t_from).seconds
    # steady state under the fault = the last 30 s of the window (a fresh fault still has a few OK ops right after the EVENT)
    if phase and win:
        t_end = t_to or ts(win[-1]); tail = [l for l in win if (t_end - ts(l)).seconds <= 30]
        win = tail if tail else win[-5:]
    if phase and span > 30 and (t_to or ts(ops[-1]) if ops else None) and not [l for l in ops if (t_to or ts(ops[-1])) and ((t_to or ts(ops[-1])) - ts(l)).seconds <= 30]:
        win = []      # nothing completed in the last 30 s of the window -> stalled
    cnt = collections.Counter((op_of(l), "ok" if is_ok(l) else "fail") for l in win)
    def n(op, kk): return sum(v for (o, k2), v in cnt.items() if o == op and k2 == kk)
    w_ok = sum(n(o, "ok") for o in ("INSERT", "UPSERT", "DELETE")); w_fail = sum(n(o, "fail") for o in ("INSERT", "UPSERT", "DELETE"))
    s_ok = n("SELECT", "ok"); s_fail = n("SELECT", "fail")
    if phase and span > 30 and len(win) == 0: level = "read-stalled" if read_only_client else "stalled"
    elif not win: level = "n/a"
    elif read_only_client: level = "read-ok" if s_ok > 0 else "read-down"
    elif w_ok > 0: level = "rw"
    elif w_fail > 0 and s_ok > 0: level = "ro"
    elif w_fail > 0: level = "down"           # writes failing and no successful read observed in the window
    elif s_ok > 0: level = "rw" if not w_fail else "ro"
    else: level = "down"
    fw = sum(w["secs"] for w in windows if w["secs"] is not None)
    # impact = union of failure windows and stall gaps (they overlap: a timed-out op is both), clipped to the phase
    iv = []
    for w in windows:
        if w["end"]:
            a_, b_ = ts(w["start"]), ts(w["end"])
            lo = max(a_, t_from) if t_from else a_; hi = min(b_, t_to) if t_to else b_
            if hi > lo: iv.append((lo, hi))
    for g in gaps:
        a_, b_ = ts(g["from"]), ts(g["to"])
        lo = max(a_, t_from) if t_from else a_; hi = min(b_, t_to) if t_to else b_
        if hi > lo: iv.append((lo, hi))
    iv.sort(); merged = []
    for lo, hi in iv:
        if merged and lo <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else: merged.append((lo, hi))
    impact = sum((hi - lo).seconds for lo, hi in merged)
    starts = [l for l in lines if "PROBE start" in l]; ends = [l for l in lines if "PROBE end" in l]
    return {"log": str(logpath), "phase": phase, "started": starts[-1][:8] if starts else None, "ended": ends[-1][:8] if ends else None,
            "ops": len(ops), "failed": len(fails), "failed_by_type": dict(collections.Counter(op_of(l) for l in fails)),
            "reconnects": max(len(recon) - (0 if phase else 1), 0), "windows": windows, "fail_window_secs": fw,
            "gaps": gaps, "stall_secs": stall, "max_gap_secs": max_gap, "impact_secs": impact, "total_impact_secs": impact,
            "events": events, "read_only_client": read_only_client,
            "window_ops": {"writes_ok": w_ok, "writes_fail": w_fail, "selects_ok": s_ok, "selects_fail": s_fail, "lines": len(win), "span_secs": span},
            "level": level, "level_zh": LEVELS[level]}

def cmd_measure(logpath, as_json=False):
    a = analyze(logpath)
    if as_json:
        import json; print(json.dumps(a, ensure_ascii=False)); return
    print(f"probe log: {logpath}")
    if a["started"]: print(f"  started : {a['started']}")
    if a["ended"]:   print(f"  ended   : {a['ended']}")
    print(f"  failed ops : {a['failed']}" + (f"   by type: {a['failed_by_type']}" if a["failed_by_type"] else ""))
    print(f"  reconnects : {a['reconnects']}  (first connect excluded)")
    if a["gaps"]:
        print(f"  stalls (gap > {GAP}s between ops): {len(a['gaps'])}, total ~{a['stall_secs']}s, longest {a['max_gap_secs']}s")
    if a["windows"]:
        print("  outage windows (first FAIL -> next OK):")
        for w in a["windows"]:
            print(f"    {w['start']} -> {w['end']}  ~{w['secs']}s" if w["secs"] is not None else f"    {w['start']} -> (no recovery in log)")
        print(f"  failure windows ~{a['fail_window_secs']}s over {len(a['windows'])} window(s); impact incl. stalls ~{a['impact_secs']}s")
    else:
        print("  no failures recorded")
    wo = a["window_ops"]
    print(f"  availability : {a['level_zh']}  (window: writes {wo['writes_ok']} ok / {wo['writes_fail']} fail, selects {wo['selects_ok']} ok / {wo['selects_fail']} fail)")
    if a["events"]:
        print("  events:"); [print("    " + l) for l in a["events"]]

def cmd_report(state_dir, hosts_path):
    """Single-line JSON: {mysql:{...}, jdbc:{...}, flight:{...}, alive:'...', faults:'...'} for the runner."""
    import json, io, contextlib
    out = {}
    for p in ("mysql", "jdbc", "flight"):
        f = pathlib_Path(state_dir) / f"probe-{p}.log"
        if f.exists() and f.stat().st_size:
            out[p] = analyze(f); out[p]["during"] = analyze(f, "during"); out[p]["after"] = analyze(f, "after")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try: cmd_alive(hosts(hosts_path))
        except BaseException as e: print(f"alive check failed: {type(e).__name__}: {str(e)[:120]}")   # hung/dead FEs must not break the report
    out["alive"] = buf.getvalue().strip()
    fl = pathlib_Path(state_dir) / "faults"
    out["faults"] = fl.read_text().strip().replace("\n", ";") if fl.exists() else ""
    print(json.dumps(out, ensure_ascii=False))

from pathlib import Path as pathlib_Path

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    op = a[0]
    if op == "status":  cmd_status(hosts(a[1]))
    elif op == "master": cmd_master(hosts(a[1]))
    elif op == "wait":   cmd_wait(hosts(a[1]), int(a[2]))
    elif op == "seed":   cmd_seed(hosts(a[1]), int(a[2]))
    elif op == "probe":  cmd_probe(hosts(a[1]), int(a[2]), a[3])
    elif op == "measure": cmd_measure(a[1], as_json=("--json" in a))
    elif op == "analyze": import json as _j; print(_j.dumps({ph: analyze(a[1], ph) for ph in (None, "during", "after")}, ensure_ascii=False))
    elif op == "report":  cmd_report(a[1], a[2])
    elif op == "resolve": cmd_resolve(hosts(a[1]), a[2])
    elif op == "role":    cmd_role(hosts(a[1]), a[2])
    elif op == "alive":   cmd_alive(hosts(a[1]))
    else: raise SystemExit(__doc__)
