// 메트릭 수집 실습-5: 지수가중이동평균이 잊어 가는 속도를 잰다.
//
// 드롭위저드 Meter 두 개와 마이크로미터 STEP 카운터 하나에 같은 사건을 똑같이 기록하고,
// 1초마다 값을 CSV 로 남긴다. /metrics 로는 Prometheus 가 긁어 갈 수 있게 내보낸다.
//
//   early : 앱이 뜰 때 만든 Meter. 부하가 오기 전에 이미 0 으로 초기화돼 있다
//   late  : 부하가 시작되는 순간 처음 만든 Meter. 첫 tick 이 부하 구간 안에서 일어난다
//   step  : 마이크로미터 SimpleMeterRegistry(CountingMode.STEP, step 60초)의 Counter
//
// 부하는 SCHEDULE 환경변수("초:초당건수,초:초당건수,...")를 순서대로 돈다. 10ms 마다 mark 한다.
import com.codahale.metrics.Meter;
import com.sun.net.httpserver.HttpServer;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.CountingMode;
import io.micrometer.core.instrument.simple.SimpleConfig;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class EwmaLab {
    static final Meter early = new Meter();
    static volatile Meter late = null;
    static volatile double targetRate = 0;
    static volatile int phase = 0;
    static final AtomicLong total = new AtomicLong();
    static Counter step;
    static final long startNanos = System.nanoTime();

    public static void main(String[] args) throws Exception {
        SimpleMeterRegistry registry = new SimpleMeterRegistry(new SimpleConfig() {
            public String get(String key) { return null; }
            public CountingMode mode() { return CountingMode.STEP; }
            public Duration step() { return Duration.ofSeconds(60); }
        }, io.micrometer.core.instrument.Clock.SYSTEM);
        step = registry.counter("orders.step");

        ScheduledExecutorService ex = Executors.newScheduledThreadPool(3);

        // 10ms 마다 targetRate/100 건을 mark 한다. 소수점은 누적해 두었다가 넘긴다.
        double[] carry = {0};
        ex.scheduleAtFixedRate(() -> {
            double want = targetRate / 100.0 + carry[0];
            long n = (long) want;
            carry[0] = want - n;
            if (n > 0) {
                if (late == null) late = new Meter();   // 부하가 처음 시작되는 순간 만든다
                early.mark(n);
                late.mark(n);
                step.increment(n);
                total.addAndGet(n);
            }
        }, 0, 10, TimeUnit.MILLISECONDS);

        // 부하 계획을 순서대로 돈다
        String schedule = System.getenv().getOrDefault("SCHEDULE", "120:0,1800:100,1800:0");
        Thread planner = new Thread(() -> {
            try {
                for (String part : schedule.split(",")) {
                    String[] kv = part.trim().split(":");
                    phase++;
                    targetRate = Double.parseDouble(kv[1]);
                    System.out.printf("phase %d: %s/s for %ss%n", phase, kv[1], kv[0]);
                    Thread.sleep(Long.parseLong(kv[0]) * 1000);
                }
                targetRate = 0;
                System.out.println("schedule done");
            } catch (InterruptedException ignored) { }
        });
        planner.setDaemon(true);
        planner.start();

        // 1초마다 CSV 한 줄. window 열은 누적 카운트로 직접 계산한 구간 평균(프로메테우스 rate 와 같은 발상)
        String csvPath = System.getenv().getOrDefault("CSV", "/data/samples.csv");
        PrintWriter csv = new PrintWriter(new FileWriter(csvPath, false), true);
        csv.println("t,target,count,early_m1,early_m5,early_m15,late_m1,late_m5,late_m15,win60,win300,step60");
        ArrayDeque<long[]> hist = new ArrayDeque<>();
        ex.scheduleAtFixedRate(() -> {
            double t = (System.nanoTime() - startNanos) / 1e9;
            long c = total.get();
            hist.addLast(new long[]{System.nanoTime(), c});
            while (hist.size() > 301) hist.removeFirst();
            Meter l = late;
            csv.println(String.format(Locale.ROOT, "%.3f,%.0f,%d,%.6f,%.6f,%.6f,%s,%s,%s,%s,%s,%.6f",
                    t, targetRate, c,
                    early.getOneMinuteRate(), early.getFiveMinuteRate(), early.getFifteenMinuteRate(),
                    l == null ? "" : fmt(l.getOneMinuteRate()),
                    l == null ? "" : fmt(l.getFiveMinuteRate()),
                    l == null ? "" : fmt(l.getFifteenMinuteRate()),
                    window(hist, 60), window(hist, 300),
                    step.count() / 60.0));
        }, 1000, 1000, TimeUnit.MILLISECONDS);

        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        HttpServer http = HttpServer.create(new InetSocketAddress(port), 0);
        http.createContext("/metrics", x -> {
            StringBuilder sb = new StringBuilder();
            sb.append("# TYPE lab_events_total counter\n");
            sb.append("lab_events_total ").append(total.get()).append('\n');
            sb.append("# TYPE lab_target_rate gauge\nlab_target_rate ").append(targetRate).append('\n');
            sb.append("# TYPE lab_ewma_rate gauge\n");
            gauge(sb, "early", "m1", early.getOneMinuteRate());
            gauge(sb, "early", "m5", early.getFiveMinuteRate());
            gauge(sb, "early", "m15", early.getFifteenMinuteRate());
            Meter l = late;
            if (l != null) {
                gauge(sb, "late", "m1", l.getOneMinuteRate());
                gauge(sb, "late", "m5", l.getFiveMinuteRate());
                gauge(sb, "late", "m15", l.getFifteenMinuteRate());
            }
            sb.append("# TYPE lab_step_rate gauge\nlab_step_rate ").append(step.count() / 60.0).append('\n');
            byte[] body = sb.toString().getBytes(StandardCharsets.UTF_8);
            x.getResponseHeaders().add("Content-Type", "text/plain; version=0.0.4");
            x.sendResponseHeaders(200, body.length);
            x.getResponseBody().write(body);
            x.close();
        });
        http.start();
        System.out.println("listening on " + port + ", schedule=" + schedule);
    }

    static String fmt(double v) { return String.format(Locale.ROOT, "%.6f", v); }

    static void gauge(StringBuilder sb, String meter, String window, double v) {
        sb.append("lab_ewma_rate{meter=\"").append(meter).append("\",window=\"").append(window)
          .append("\"} ").append(v).append('\n');
    }

    // 최근 sec 초 동안 늘어난 건수 / 실제 경과 시간. 표본이 모자라면 빈칸
    static String window(ArrayDeque<long[]> h, int sec) {
        if (h.size() <= sec) return "";
        long[] last = h.peekLast();
        long[] first = null;
        int i = 0, idx = h.size() - 1 - sec;
        for (long[] e : h) { if (i++ == idx) { first = e; break; } }
        double dt = (last[0] - first[0]) / 1e9;
        return fmt((last[1] - first[1]) / dt);
    }
}
