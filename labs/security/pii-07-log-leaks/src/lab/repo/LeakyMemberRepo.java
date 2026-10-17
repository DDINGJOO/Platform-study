package lab.repo;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import lab.LabCrypto;

/** ③ 새는 쪽: 드라이버 예외를 원인으로 달아 다시 던진다. */
public class LeakyMemberRepo implements MemberRepo {
    private final Connection c;
    public LeakyMemberRepo(Connection c) { this.c = c; }

    @Override
    public long insert(String rrnPlain, String phone) {
        try (PreparedStatement ps = c.prepareStatement(
                "INSERT INTO member (rrn_enc, phone) VALUES (?, ?)", PreparedStatement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, LabCrypto.encrypt(rrnPlain));
            ps.setString(2, phone);
            ps.executeUpdate();
            try (var rs = ps.getGeneratedKeys()) { rs.next(); return rs.getLong(1); }
        } catch (SQLException e) {
            throw new IllegalStateException("회원 저장 실패", e);
        }
    }
}
