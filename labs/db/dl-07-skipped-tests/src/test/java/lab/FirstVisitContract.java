package lab;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

/** 어느 DB 에서 돌리든 같은 기대: 동시 요청 3개가 전부 성공하고 카운트가 3 이어야 한다. */
abstract class FirstVisitContract {

    static final int ROUNDS = 30;
    static final int THREADS = 3;

    abstract FirstVisitScenario scenario();
    abstract String label();

    @Test
    void 첫_방문_동시_요청_3개가_전부_성공한다() throws Exception {
        String impl = System.getProperty("lab.impl", "buggy");
        FirstVisitScenario s = scenario();
        s.createTable();
        FirstVisitScenario.Result r = s.run(impl, ROUNDS, THREADS);
        System.out.println("[" + label() + "] impl=" + impl + " " + r);
        assertEquals(0, r.failed(), "실패한 요청: " + r.errors());
        assertEquals(0, r.wrongCounts(), "cnt 가 " + THREADS + " 이 아닌 키 수");
    }
}
