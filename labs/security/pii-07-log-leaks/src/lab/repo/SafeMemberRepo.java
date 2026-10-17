package lab.repo;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import lab.LabCrypto;

/** ③ 막은 쪽: 원인을 떼고 SQLState·오류 코드·요청 식별자만 담아 다시 던진다. */
public class SafeMemberRepo implements MemberRepo {
    private final Connection c;
    public SafeMemberRepo(Connection c) { this.c = c; }

    @Override
    public long insert(String rrnPlain, String phone) {
        try (PreparedStatement ps = c.prepareStatement(
                "INSERT INTO member (rrn_enc, phone) VALUES (?, ?)", PreparedStatement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, LabCrypto.encrypt(rrnPlain));
            ps.setString(2, phone);
            ps.executeUpdate();
            try (var rs = ps.getGeneratedKeys()) { rs.next(); return rs.getLong(1); }
        } catch (SQLException e) {
            throw new MemberSaveException("회원 저장 실패 (sqlState=" + e.getSQLState()
                    + ", errorCode=" + e.getErrorCode() + ")");
        }
    }

    public static class MemberSaveException extends RuntimeException {
        public MemberSaveException(String m) { super(m); }
    }
}
