package lab.upsert;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * "없으면 넣기" 다섯 패턴. 요청 하나 = 트랜잭션 하나(재시도 없음).
 * 반환값은 이 요청이 스스로 내린 판정이다. SAVED(내가 넣었다) 또는 DUPLICATE(이미 있었다).
 * 예외는 잡지 않고 그대로 던진다(실패로 센다). 단, 패턴 자체가 예외를 판정에 쓰는 ③ ④ 는 1062 만 잡는다.
 *
 * 표: visit(id PK auto, user_key 유니크, payload, inserted_by)
 * inserted_by 는 실제로 행을 넣은 요청의 id 다. 판정이 맞았는지 채점할 때만 쓴다(패턴은 읽지 않는다).
 */
public final class Patterns {

    public enum Verdict { SAVED, DUPLICATE, CONFLICT, UNKNOWN }

    private Patterns() {}

    public static Verdict run(String pattern, Connection c, String key, String payload, String reqId, Step step) throws SQLException {
        return switch (pattern) {
            case "p1" -> p1InsertIgnoreThenForUpdate(c, key, payload, reqId, step);
            case "p2", "p2a" -> p2OdkuNoop(c, key, payload, reqId, step);
            case "p3" -> p3InsertCatchDuplicate(c, key, payload, reqId, step);
            case "p4" -> p4ReadThenBranch(c, key, payload, reqId, step, false);
            case "p4b" -> p4ReadThenBranch(c, key, payload, reqId, step, true);
            case "p5" -> p5ForUpdateFirst(c, key, payload, reqId, step);
            default -> throw new IllegalArgumentException(pattern);
        };
    }

    /** 단계 사이에 끼어들 수 있게 한다(잠금 덤프용). 벤치에서는 아무것도 안 한다. */
    public interface Step { void at(String label) throws SQLException; Step NONE = l -> {}; }

    // ① INSERT IGNORE 다음 같은 행에 SELECT ... FOR UPDATE
    static Verdict p1InsertIgnoreThenForUpdate(Connection c, String key, String payload, String reqId, Step step) throws SQLException {
        int n = insert(c, "INSERT IGNORE INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key, payload, reqId);
        step.at("after INSERT IGNORE (affected=" + n + ")");
        try (PreparedStatement ps = c.prepareStatement("SELECT id, payload FROM visit WHERE user_key=? FOR UPDATE")) {
            ps.setString(1, key);
            try (ResultSet rs = ps.executeQuery()) { rs.next(); }
        }
        step.at("after SELECT FOR UPDATE");
        c.commit();
        return n == 1 ? Verdict.SAVED : Verdict.DUPLICATE;
    }

    // ② INSERT ... ON DUPLICATE KEY UPDATE 무변경(payload=payload). 반환값으로 판정한다.
    static Verdict p2OdkuNoop(Connection c, String key, String payload, String reqId, Step step) throws SQLException {
        int n = insert(c, "INSERT INTO visit(user_key, payload, inserted_by) VALUES (?,?,?) ON DUPLICATE KEY UPDATE payload=payload", key, payload, reqId);
        step.at("after ODKU (affected=" + n + ")");
        c.commit();
        return n == 1 ? Verdict.SAVED : Verdict.DUPLICATE;
    }

    // ③ 일반 INSERT, 1062 를 잡아 중복으로 끝낸다.
    static Verdict p3InsertCatchDuplicate(Connection c, String key, String payload, String reqId, Step step) throws SQLException {
        try {
            insert(c, "INSERT INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key, payload, reqId);
            step.at("after INSERT");
            c.commit();
            return Verdict.SAVED;
        } catch (SQLException e) {
            if (e.getErrorCode() != 1062) throw e;
            step.at("after INSERT (1062)");
            c.rollback();
            return Verdict.DUPLICATE;
        }
    }

    // ④ 잠금 없는 조회로 먼저 확인하고, 없을 때만 INSERT. 1062 면 다시 읽어 같은 값인지 본다.
    //    recheckInSameTx=false: 1062 뒤 롤백하고 새 트랜잭션에서 다시 읽는다(④).
    //    recheckInSameTx=true : 같은 트랜잭션에서 다시 읽는다(④b, RR 함정 확인용).
    static Verdict p4ReadThenBranch(Connection c, String key, String payload, String reqId, Step step, boolean recheckInSameTx) throws SQLException {
        String found = plainRead(c, key);
        step.at("after plain SELECT (found=" + (found != null) + ")");
        if (found != null) {
            c.commit();
            return found.equals(payload) ? Verdict.DUPLICATE : Verdict.CONFLICT;
        }
        try {
            insert(c, "INSERT INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key, payload, reqId);
            step.at("after INSERT");
            c.commit();
            return Verdict.SAVED;
        } catch (SQLException e) {
            if (e.getErrorCode() != 1062) throw e;
            if (!recheckInSameTx) c.rollback();
            String again = plainRead(c, key);
            c.commit();
            if (again == null) return Verdict.UNKNOWN;          // 중복이라는데 행이 안 보인다
            return again.equals(payload) ? Verdict.DUPLICATE : Verdict.CONFLICT;
        }
    }

    // ⑤ 없는 행에 SELECT ... FOR UPDATE 를 먼저 걸고, 없으면 INSERT.
    static Verdict p5ForUpdateFirst(Connection c, String key, String payload, String reqId, Step step) throws SQLException {
        boolean exists;
        try (PreparedStatement ps = c.prepareStatement("SELECT id FROM visit WHERE user_key=? FOR UPDATE")) {
            ps.setString(1, key);
            try (ResultSet rs = ps.executeQuery()) { exists = rs.next(); }
        }
        step.at("after SELECT FOR UPDATE (exists=" + exists + ")");
        if (exists) {
            c.commit();
            return Verdict.DUPLICATE;
        }
        insert(c, "INSERT INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key, payload, reqId);
        step.at("after INSERT");
        c.commit();
        return Verdict.SAVED;
    }

    static int insert(Connection c, String sql, String key, String payload, String reqId) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, key);
            ps.setString(2, payload);
            ps.setString(3, reqId);
            return ps.executeUpdate();
        }
    }

    static String plainRead(Connection c, String key) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("SELECT payload FROM visit WHERE user_key=?")) {
            ps.setString(1, key);
            try (ResultSet rs = ps.executeQuery()) { return rs.next() ? rs.getString(1) : null; }
        }
    }
}
