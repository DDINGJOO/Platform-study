package lab;

/** H2 의 MySQL 호환 모드로 같은 시나리오. */
class H2MysqlModeTest extends FirstVisitContract {
    @Override FirstVisitScenario scenario() {
        return new FirstVisitScenario("jdbc:h2:mem:dl07;MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=10000", "sa", "");
    }
    @Override String label() { return "H2 MODE=MySQL"; }
}
