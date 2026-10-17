package lab;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/** 실제 MySQL 8.4 로 같은 시나리오. Docker 를 못 찾으면 실패 대신 SKIPPED. */
@Testcontainers(disabledWithoutDocker = true)
class SkippingMysqlTest extends FirstVisitContract {

    @Container
    static final GenericContainer<?> MYSQL = new GenericContainer<>("mysql:8.4")
            .withEnv("MYSQL_ROOT_PASSWORD", "lab")
            .withEnv("MYSQL_DATABASE", "lab")
            .withCommand("--innodb-print-all-deadlocks=ON")
            .withExposedPorts(3306)
            .waitingFor(Wait.forLogMessage(".*ready for connections.*port: 3306.*", 1));

    @Override FirstVisitScenario scenario() {
        String url = "jdbc:mysql://" + MYSQL.getHost() + ":" + MYSQL.getMappedPort(3306) + "/lab";
        return new FirstVisitScenario(url, "root", "lab");
    }
    @Override String label() { return "MySQL 8.4 / Testcontainers " + System.getProperty("lab.tcVersion"); }
}
