package lab.upsert;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.resilience.annotation.EnableResilientMethods;

/**
 * 모드
 *   bench <p1|p2|p2a|p3|p4|p4b|p5> <RR|RC> <rounds>      재시도 없이 4건 동시 x rounds
 *   retry <pattern> <RR|RC> <rounds>                       같은 요청을 RetryTemplate 으로 트랜잭션 바깥에서 재시도
 *   footprint <pattern> <RR|RC>                            세션 하나가 커밋 직전까지 잡는 잠금
 *   deadlock <p1|p5> <RR|RC>                               교착 직전 data_locks
 *   spring <plain|retry> <rounds>                          ① 을 JdbcTemplate + @Transactional(+@Retryable) 로
 *   order                                                  @Retryable + @Transactional 순서 확인
 */
@SpringBootApplication
@EnableResilientMethods
public class UpsertApplication {

    public static void main(String[] args) { SpringApplication.run(UpsertApplication.class, args); }

    @Bean
    CommandLineRunner runner(VisitService svc, JdbcTemplate jdbc) {
        return args -> {
            String mode = args[0];
            switch (mode) {
                case "bench" -> Bench.run(args[1], args[2], Integer.parseInt(args[3]), false);
                case "retry" -> Bench.run(args[1], args[2], Integer.parseInt(args[3]), true);
                case "footprint" -> LockDump.footprint(args[1], args[2]);
                case "deadlock" -> LockDump.deadlock(args[1], args[2]);
                case "spring" -> spring(svc, args[1].equals("retry"), Integer.parseInt(args[2]));
                case "order" -> order(svc, jdbc);
                default -> throw new IllegalArgumentException(mode);
            }
        };
    }

    static void spring(VisitService svc, boolean retry, int rounds) throws Exception {
        Bench.reset();
        Map<String, Integer> counts = new TreeMap<>();
        ExecutorService pool = Executors.newFixedThreadPool(Bench.WORKERS);
        try {
            for (int round = 0; round < rounds; round++) {
                String key = Bench.randKey();
                CyclicBarrier b = new CyclicBarrier(Bench.WORKERS);
                List<Future<String>> fs = new ArrayList<>();
                for (int w = 0; w < Bench.WORKERS; w++) {
                    String reqId = "r" + round + "-w" + w;
                    fs.add(pool.submit(() -> {
                        b.await();
                        try {
                            return (retry ? svc.p1WithRetry(key, reqId) : svc.p1Plain(key, reqId)).name();
                        } catch (RuntimeException e) {
                            return "fail:" + e.getClass().getSimpleName();
                        }
                    }));
                }
                for (Future<String> f : fs) counts.merge(f.get(), 1, Integer::sum);
            }
        } finally { pool.shutdownNow(); }
        System.out.printf("spring p1 %s rounds=%d requests=%d%n  results=%s%n  attempts=%d%n",
                retry ? "@Retryable+@Transactional" : "@Transactional", rounds, rounds * Bench.WORKERS, counts, svc.attempts());
    }

    static void order(VisitService svc, JdbcTemplate jdbc) throws Exception {
        Bench.reset();
        String r = svc.failOnce("order");
        svc.trace().forEach(t -> System.out.println("  " + t));
        System.out.println("  result: " + r);
        System.out.println("  rows left: " + jdbc.queryForList("SELECT user_key FROM visit WHERE inserted_by='order' ORDER BY user_key", String.class));
    }
}
