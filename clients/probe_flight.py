#!/usr/bin/env python3
"""Arrow Flight SQL probe (ADBC) against Doris FE :8070. Result batches come straight from the BE
Flight endpoints, so this client must reach the BEs (it runs inside the VPC). Host-list failover done here.
If Doris rejects DML over Flight SQL the loop degrades to SELECT-only and says so in the log."""
import probe_common as pc
from adbc_driver_flightsql import dbapi as flight

class Conn:
    def __init__(self, c): self.c = c; self.cols = []
    def execute(self, sql):
        with self.c.cursor() as cur:
            cur.execute(sql)
            self.cols = [d[0] for d in cur.description] if cur.description else []
            return [tuple(r) for r in cur.fetchall()] if cur.description else []
    def close(self): self.c.close()

class Driver:
    dml_error = ""
    table = "hatest.events"
    def __init__(self): self._last = None
    def connect(self, ip):
        c = flight.connect(f"grpc://{ip}:8070",
                           db_kwargs={"username": "root", "password": "",
                                      "adbc.flight.sql.rpc.timeout_seconds.query": "8",
                                      "adbc.flight.sql.rpc.timeout_seconds.fetch": "8",
                                      "adbc.flight.sql.rpc.timeout_seconds.update": "8"},
                           autocommit=True)
        self._last = Conn(c); return self._last
    def last_columns(self): return self._last.cols if self._last else []
    def dml_ok(self, conn):
        """Doris documents Flight SQL as a query path. Try a sentinel INSERT + DELETE and verify by reading back;
        anything short of a fully consistent round trip counts as unsupported."""
        try:
            conn.execute("INSERT INTO hatest.events VALUES (99, now(), 'flight-dml-probe', 7)")
            if conn.execute("SELECT ver FROM hatest.events WHERE id = 99") != [(7,)]:
                raise RuntimeError("insert not visible")
            conn.execute("DELETE FROM hatest.events WHERE id = 99")
            if conn.execute("SELECT ver FROM hatest.events WHERE id = 99"):
                raise RuntimeError("delete not applied")
            return True
        except Exception as e:
            self.dml_error = f"{type(e).__name__}: {str(e).split('error msg:')[-1].strip()}"
            return False

if __name__ == "__main__":
    a = pc.parse_args("arrow-flight")
    pc.run("arrow-flight", Driver(), pc.read_hosts(a.hosts_file), a.base, a.log, a.seconds)
