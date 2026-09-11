"""Shared probe loop for the Python clients (mysql, arrow-flight). One op per second on one key:
INSERT(ver=1) -> UPSERT(ver=2) -> SELECT(expect ver=2) -> DELETE -> SELECT(expect gone), then next key.
A driver supplies connect(host) -> object with .execute(sql) -> list of rows and .close().
Log format is shared with cluster.py measure."""
import time, datetime, argparse, collections

OPS = ("INSERT", "UPSERT", "SELECT", "DELETE", "SELECT")
TABLE = "events"

def parse_args(proto):
    ap = argparse.ArgumentParser(description=f"{proto} probe")
    ap.add_argument("--hosts-file", required=True, help="lines: <name> <ip>")
    ap.add_argument("--log", required=True)
    ap.add_argument("--seconds", type=int, default=86400)
    ap.add_argument("--base", type=int, default=1_000_000, help="key range start (per client)")
    return ap.parse_args()

def read_hosts(path):
    hs = []
    for line in open(path):
        p = line.split()
        if len(p) >= 2:
            hs.append({"name": p[0], "ip": p[1]})
    return hs

def name_of(hs, ip):
    return next((h["name"] for h in hs if h["ip"] == ip), ip)

def run(proto, driver, hs, base, logpath, seconds):
    TABLE = getattr(driver, "table", "events")     # flight has no session database -> fully qualified
    log = open(logpath, "a")
    def out(msg):
        line = f"{datetime.datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True); log.write(line + "\n"); log.flush()

    conn = None; via = "-"; just_failed = False; i = ok = fail = reconnects = 0
    per_op = collections.Counter(); per_op_fail = collections.Counter()
    ops = OPS; read_only = False
    t0 = time.time(); k = base + (int(t0) % 100_000) * 10; step = 0
    out(f"PROBE start proto={proto} hosts={','.join(h['name'] for h in hs)} duration={seconds}s cycle={'>'.join(OPS)}")

    def connect():
        nonlocal conn, via, reconnects
        last = None
        for h in hs:
            try:
                conn = driver.connect(h["ip"]); via = h["name"]; reconnects += 1
                try:  # which FE are we actually on (JDBC-style failover may pick another host)
                    rows = conn.execute("SHOW FRONTENDS")
                    cols = driver.last_columns()
                    if "CurrentConnected" in cols and "Host" in cols:
                        ci, hi = cols.index("CurrentConnected"), cols.index("Host")
                        cur = next((r for r in rows if str(r[ci]).lower() == "yes"), None)
                        if cur: via = name_of(hs, cur[hi])
                except Exception:
                    pass
                out(f"connected to {via} ({h['ip']})")
                return
            except Exception as e:
                last = e
        raise last

    def fe_state():
        for sql in ("SHOW FRONTENDS", "SELECT Host, IsMaster, Alive FROM frontends()"):   # 2nd form works over Flight SQL
            try:
                rows = conn.execute(sql); cols = driver.last_columns()
                hi, mi, ai = cols.index("Host"), cols.index("IsMaster"), cols.index("Alive")
                return " ".join(f"{name_of(hs, r[hi])}:{'M' if str(r[mi])=='true' else 'f'}:{'up' if str(r[ai])=='true' else 'DOWN'}"
                                for r in sorted(rows, key=lambda r: r[hi]))
            except Exception:
                continue
        return "?"

    while time.time() - t0 < seconds:
        i += 1; op = ops[step]
        try:
            if conn is None:
                connect()
                if not read_only and not driver.dml_ok(conn):
                    read_only = True; ops = ("SELECT",)
                    out(f"DML unsupported over {proto} ({driver.dml_error[:120]}) — switching to SELECT-only mode")
                    step = 0; op = ops[0]
            if read_only:
                rows = conn.execute(f"SELECT ver FROM {TABLE} WHERE id = 1")   # seed row must exist
                if not rows: raise RuntimeError("verify id=1: seed row missing")
            elif op == "INSERT":
                conn.execute(f"INSERT INTO {TABLE} VALUES ({k}, now(), '{proto}', 1)")
            elif op == "UPSERT":
                conn.execute(f"INSERT INTO {TABLE} VALUES ({k}, now(), '{proto}-updated', 2)")
            elif op == "DELETE":
                conn.execute(f"DELETE FROM {TABLE} WHERE id = {k}")
            else:
                rows = conn.execute(f"SELECT ver FROM {TABLE} WHERE id = {k}")
                want = 2 if step == 2 else None
                got = rows[0][0] if rows else None
                if got != want: raise RuntimeError(f"verify id={k}: want ver={want} got {got}")
            cnt = conn.execute(f"SELECT count(*) FROM {TABLE}")[0][0]
            ok += 1; per_op[op] += 1
            out(f"#{i} OK {op:6} id={k} via {via} rows={cnt} [{fe_state()}]" + (" (recovered)" if just_failed else ""))
            just_failed = False
            if not read_only:
                step += 1
                if step == len(ops): step = 0; k += 1
        except Exception as e:
            fail += 1; per_op_fail[op] += 1; just_failed = True
            out(f"#{i} FAIL {op:6} id={k} via {via}: {type(e).__name__}: {str(e)[:110]}")
            try: conn.close()
            except Exception: pass
            conn = None
            if op in ("INSERT", "UPSERT", "DELETE"):
                # a failed write says nothing about reads: probe the seed row on a fresh connection so
                # measure can tell "only writes are down" (只讀) from "everything is down" (不可用)
                cvia = "-"
                try:
                    cconn = None
                    for h in hs:
                        try: cconn = driver.connect(h["ip"]); cvia = h["name"]; break
                        except Exception: continue
                    if cconn is None: raise RuntimeError("no FE reachable")
                    rows = cconn.execute(f"SELECT ver FROM {TABLE} WHERE id = 1")
                    out(f"#{i} OK SELECT(check) id=1 via {cvia}" + ("" if rows else " (seed row missing)"))
                    cconn.close()
                except Exception as e2:
                    out(f"#{i} FAIL SELECT(check) id=1 via {cvia}: {type(e2).__name__}: {str(e2)[:90]}")
            if not read_only: step = 0; k += 1
        time.sleep(1)
    ops_s = " ".join(f"{o}={per_op[o]}/{per_op[o]+per_op_fail[o]}" for o in dict.fromkeys(ops))
    out(f"PROBE end proto={proto} ok={ok} fail={fail} reconnects={reconnects} per-op(ok/total) {ops_s}")
