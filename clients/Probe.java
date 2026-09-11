import java.io.FileWriter;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.*;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** JDBC probe: MySQL Connector/J multi-host URL, the driver does the failover.
 *  Same op cycle and log format as the Python probes.
 *  Usage: java -cp .:mysql-connector-j.jar Probe <hosts-file> <log> <seconds> <key-base> */
public class Probe {
    static final String[] OPS = {"INSERT", "UPSERT", "SELECT", "DELETE", "SELECT"};
    static PrintWriter log; static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("HH:mm:ss");
    static Map<String, String> nameOf = new LinkedHashMap<>();

    static void out(String m) { String l = LocalTime.now().format(TS) + " " + m; System.out.println(l); log.println(l); log.flush(); }
    static String name(String ip) { return nameOf.getOrDefault(ip, ip); }

    public static void main(String[] a) throws Exception {
        List<String> ips = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(a[0]))) { String[] p = line.trim().split("\\s+"); if (p.length >= 2) { nameOf.put(p[1], p[0]); ips.add(p[1]); } }
        log = new PrintWriter(new FileWriter(a[1], true));
        int seconds = Integer.parseInt(a[2]); long base = Long.parseLong(a[3]);
        StringBuilder hosts = new StringBuilder();
        for (String ip : ips) { if (hosts.length() > 0) hosts.append(','); hosts.append(ip).append(":9030"); }
        String url = "jdbc:mysql://" + hosts + "/hatest?failOverReadOnly=false&connectTimeout=3000&socketTimeout=8000"
                   + "&autoReconnect=false&useSSL=false&allowPublicKeyRetrieval=true";
        long t0 = System.currentTimeMillis(); long k = base + (t0 / 1000 % 100000) * 10; int step = 0;
        int i = 0, ok = 0, fail = 0, reconnects = 0; boolean justFailed = false; String via = "-";
        Map<String, int[]> perOp = new LinkedHashMap<>(); for (String o : OPS) perOp.put(o, new int[2]);
        Connection conn = null;
        out("PROBE start proto=jdbc hosts=" + String.join(",", nameOf.values()) + " duration=" + seconds + "s cycle=" + String.join(">", OPS) + " url=" + url.replaceAll("\\?.*", ""));
        while (System.currentTimeMillis() - t0 < seconds * 1000L) {
            i++; String op = OPS[step];
            try {
                if (conn == null) {
                    conn = DriverManager.getConnection(url, "root", ""); conn.setAutoCommit(true); reconnects++;
                    via = currentFe(conn, via); out("connected to " + via + " (driver-selected host)");
                }
                try (Statement st = conn.createStatement()) {
                    switch (op) {
                        case "INSERT": st.executeUpdate("INSERT INTO events VALUES (" + k + ", now(), 'jdbc', 1)"); break;
                        case "UPSERT": st.executeUpdate("INSERT INTO events VALUES (" + k + ", now(), 'jdbc-updated', 2)"); break;
                        case "DELETE": st.executeUpdate("DELETE FROM events WHERE id = " + k); break;
                        default: {
                            Integer want = step == 2 ? 2 : null; Integer got = null;
                            try (ResultSet rs = st.executeQuery("SELECT ver FROM events WHERE id = " + k)) { if (rs.next()) got = rs.getInt(1); }
                            if (!Objects.equals(got, want)) throw new SQLException("verify id=" + k + ": want ver=" + want + " got " + got);
                        }
                    }
                    long cnt; try (ResultSet rs = st.executeQuery("SELECT count(*) FROM events")) { rs.next(); cnt = rs.getLong(1); }
                    String fe = feState(st);
                    ok++; perOp.get(op)[0]++;
                    out("#" + i + " OK " + String.format("%-6s", op) + " id=" + k + " via " + via + " rows=" + cnt + " [" + fe + "]" + (justFailed ? " (recovered)" : ""));
                    justFailed = false;
                    step++; if (step == OPS.length) { step = 0; k++; }
                }
            } catch (Exception e) {
                fail++; perOp.get(op)[1]++; justFailed = true;
                String msg = e.getMessage() == null ? "" : e.getMessage().replace('\n', ' ');
                out("#" + i + " FAIL " + String.format("%-6s", op) + " id=" + k + " via " + via + ": " + e.getClass().getSimpleName() + ": " + msg.substring(0, Math.min(110, msg.length())));
                try { if (conn != null) conn.close(); } catch (Exception ignore) {}
                conn = null;
                if (!op.equals("SELECT")) {   // read check on a fresh connection: are reads still fine while writes fail?
                    String cvia = "-";
                    try (Connection cc = DriverManager.getConnection(url, "root", "")) {
                        cvia = currentFe(cc, "-");
                        try (Statement st = cc.createStatement(); ResultSet rs = st.executeQuery("SELECT ver FROM events WHERE id = 1")) {
                            out("#" + i + " OK SELECT(check) id=1 via " + cvia + (rs.next() ? "" : " (seed row missing)"));
                        }
                    } catch (Exception e2) {
                        String m2 = e2.getMessage() == null ? "" : e2.getMessage().replace('\n', ' ');
                        out("#" + i + " FAIL SELECT(check) id=1 via " + cvia + ": " + e2.getClass().getSimpleName() + ": " + m2.substring(0, Math.min(90, m2.length())));
                    }
                }
                step = 0; k++;
            }
            Thread.sleep(1000);
        }
        StringBuilder ops = new StringBuilder();
        for (String o : new LinkedHashSet<>(Arrays.asList(OPS))) ops.append(o).append('=').append(perOp.get(o)[0]).append('/').append(perOp.get(o)[0] + perOp.get(o)[1]).append(' ');
        out("PROBE end proto=jdbc ok=" + ok + " fail=" + fail + " reconnects=" + reconnects + " per-op(ok/total) " + ops.toString().trim());
        log.close();
    }

    /** Which FE did the driver land on? SHOW FRONTENDS marks it with CurrentConnected=Yes. */
    static String currentFe(Connection c, String dflt) {
        try (Statement st = c.createStatement(); ResultSet rs = st.executeQuery("SHOW FRONTENDS")) {
            while (rs.next()) if ("Yes".equalsIgnoreCase(rs.getString("CurrentConnected"))) return name(rs.getString("Host"));
        } catch (Exception ignore) {}
        return dflt;
    }
    static String feState(Statement st) {
        try (ResultSet rs = st.executeQuery("SHOW FRONTENDS")) {
            TreeMap<String, String> m = new TreeMap<>();
            while (rs.next()) m.put(rs.getString("Host"), name(rs.getString("Host")) + ":" + ("true".equals(rs.getString("IsMaster")) ? "M" : "f") + ":" + ("true".equals(rs.getString("Alive")) ? "up" : "DOWN"));
            return String.join(" ", m.values());
        } catch (Exception e) { return "?"; }
    }
}
