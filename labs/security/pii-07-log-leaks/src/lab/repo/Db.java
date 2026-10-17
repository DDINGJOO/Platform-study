package lab.repo;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

public final class Db {
    private Db() {}

    public static Connection open() throws SQLException {
        Connection c = DriverManager.getConnection("jdbc:h2:mem:lab;DB_CLOSE_DELAY=-1");
        try (Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS member");
            s.execute("CREATE TABLE member (id BIGINT AUTO_INCREMENT PRIMARY KEY,"
                    + " rrn_enc VARCHAR(120) NOT NULL CONSTRAINT uk_member_rrn UNIQUE,"
                    + " phone VARCHAR(40) NOT NULL CONSTRAINT uk_member_phone UNIQUE)");
        }
        return c;
    }
}
