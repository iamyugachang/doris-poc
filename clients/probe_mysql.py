#!/usr/bin/env python3
"""MySQL-protocol probe (pymysql) against Doris FE :9030. Host-list failover done here."""
import pymysql
import probe_common as pc

class Conn:
    def __init__(self, c): self.c = c; self.cols = []
    def execute(self, sql):
        with self.c.cursor() as cur:
            cur.execute(sql)
            self.cols = [d[0] for d in cur.description] if cur.description else []
            return list(cur.fetchall()) if cur.description else []
    def close(self): self.c.close()

class Driver:
    dml_error = ""
    def __init__(self): self._last = None
    def connect(self, ip):
        c = pymysql.connect(host=ip, port=9030, user="root", password="", database="hatest",
                            connect_timeout=3, read_timeout=8, write_timeout=8, autocommit=True)
        self._last = Conn(c); return self._last
    def last_columns(self): return self._last.cols if self._last else []
    def dml_ok(self, conn): return True

if __name__ == "__main__":
    a = pc.parse_args("mysql")
    pc.run("mysql", Driver(), pc.read_hosts(a.hosts_file), a.base, a.log, a.seconds)
