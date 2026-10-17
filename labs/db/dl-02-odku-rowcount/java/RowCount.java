import java.nio.file.*;
import java.sql.*;
import java.util.*;

// 사용: java -cp <connector-j.jar> java/RowCount.java <모드이름> <JDBC URL>
public class RowCount {
    static final String RESET1 = "DELETE FROM item";
    static final String RESET2 = "INSERT INTO item(id,code,v,hits) VALUES (1,'a',1,0)";

    public static void main(String[] a) throws Exception {
        String mode = a[0], url = a[1];
        try (Connection c = DriverManager.getConnection(url, "root", "lab")) {
            DatabaseMetaData md = c.getMetaData();
            System.out.printf("# mode=%s driver=%s %s server=%s%n", mode,
                    md.getDriverName(), md.getDriverVersion(), md.getDatabaseProductVersion());
            System.out.printf("%-4s %-8s %-11s %-10s %-11s %s%n", "case", "update", "ROW_COUNT()", "warnings", "ROW_COUNT()²", "설명");
            for (String line : Files.readAllLines(Path.of("sql/cases.txt"))) {
                if (line.isBlank() || line.startsWith("#")) continue;
                String[] p = line.split("\\|", 3);
                try (Statement s = c.createStatement()) {
                    s.executeUpdate(RESET1);
                    s.executeUpdate(RESET2);
                    String upd, rc = "-", w = "-", rc2 = "-";
                    try {
                        int n = s.executeUpdate(p[2]);
                        upd = Integer.toString(n);
                        rc = one(s, "SELECT ROW_COUNT()");            // 문장 바로 다음
                        s.executeUpdate(RESET1);
                        s.executeUpdate(RESET2);
                        s.executeUpdate(p[2]);
                        List<String> codes = new ArrayList<>();
                        for (SQLWarning x = s.getWarnings(); x != null; x = x.getNextWarning()) codes.add(Integer.toString(x.getErrorCode()));
                        w = codes.isEmpty() ? "0" : String.join(",", codes);
                        rc2 = one(s, "SELECT ROW_COUNT()");           // getWarnings() 를 부른 다음
                    } catch (SQLException e) {
                        upd = "ERR " + e.getErrorCode();
                        w = e.getClass().getSimpleName();
                    }
                    System.out.printf("%-4s %-8s %-11s %-10s %-11s %s%n", p[0], upd, rc, w, rc2, p[1]);
                }
            }
            snapshot(url, "REPEATABLE READ");
            snapshot(url, "READ COMMITTED");
        }
    }

    // INSERT IGNORE 가 0 을 돌려준 뒤, 같은 트랜잭션의 잠금 없는 조회로 기존 행이 보이는가
    static void snapshot(String url, String iso) throws Exception {
        try (Connection a = DriverManager.getConnection(url, "root", "lab");
             Connection b = DriverManager.getConnection(url, "root", "lab");
             Statement sa = a.createStatement(); Statement sb = b.createStatement()) {
            sb.executeUpdate(RESET1);
            sb.executeUpdate(RESET2);
            sa.execute("SET SESSION TRANSACTION ISOLATION LEVEL " + iso);
            a.setAutoCommit(false);
            try (ResultSet r = sa.executeQuery("SELECT COUNT(*) FROM item")) { r.next(); }  // 읽기 뷰가 여기서 생긴다(RR)
            sb.executeUpdate("INSERT INTO item(code,v) VALUES('n',1)");                    // b 는 autocommit
            int ig = sa.executeUpdate("INSERT IGNORE INTO item(code,v) VALUES('n',1)");
            int plain = count(sa, "SELECT COUNT(*) FROM item WHERE code='n'");
            int share = count(sa, "SELECT COUNT(*) FROM item WHERE code='n' FOR SHARE");
            a.rollback();
            System.out.printf("# snapshot %-16s INSERT IGNORE=%d  잠금없는 SELECT=%d행  FOR SHARE=%d행%n", iso, ig, plain, share);
        }
    }

    static String one(Statement s, String q) throws SQLException {
        try (ResultSet r = s.executeQuery(q)) { r.next(); return r.getString(1); }
    }

    static int count(Statement s, String q) throws SQLException {
        try (ResultSet r = s.executeQuery(q)) { r.next(); return r.getInt(1); }
    }
}
