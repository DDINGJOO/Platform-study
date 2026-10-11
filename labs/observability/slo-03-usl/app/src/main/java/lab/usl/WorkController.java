package lab.usl;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.LongAdder;
import java.util.concurrent.locks.LockSupport;
import java.util.concurrent.locks.ReentrantLock;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 요청 하나 = 병렬 구간 + 직렬 구간.
 *
 *   병렬 구간  parallelUs 만큼 잠든다(I/O 대기 흉내). 요청끼리 서로 막지 않는다.
 *   CPU 구간   cpuUs 만큼(벽시계) 또는 cpuLoops 번(일의 양 고정) CPU 를 쓴다. 코어 수가 상한이 된다.
 *   직렬 구간  전역 락 하나를 잡고 serialUs 만큼 머문다(기본은 CPU 를 돌려서) → 경합(σ)
 *   expRandom 을 켜면 병렬·직렬 구간 길이를 설정값을 평균으로 하는 지수 분포에서 뽑는다.
 *              락을 잡은 채로, 지금 같이 들어와 있는 다른 요청 수 × coherencyUs 만큼 더 머문다
 *              (공유 상태를 바꿀 때 다른 요청 모두와 맞추는 비용)  → 일관성(κ)
 *
 * 값은 환경변수로 시작값을 주고, POST /config 로 재시작 없이 바꾼다.
 */
@RestController
public class WorkController {

    private final ReentrantLock lock = new ReentrantLock();
    private final AtomicInteger inFlight = new AtomicInteger();

    private final LongAdder count = new LongAdder();
    private final LongAdder lockWaitNs = new LongAdder();
    private final LongAdder lockHoldNs = new LongAdder();
    private final LongAdder peersSum = new LongAdder();

    private volatile long parallelUs = env("PARALLEL_US", 20_000);
    private volatile long serialUs = env("SERIAL_US", 1_000);
    private volatile long coherencyUs = env("COHERENCY_US", 0);
    private volatile long cpuUs = env("CPU_US", 0);
    // cpuUs 는 "벽시계로 그만큼 돌기"라서, 코어를 뺏긴 동안에도 시간이 흘러 일의 양이 줄어든다.
    // cpuLoops 는 정해진 횟수만큼 계산한다. 코어를 뺏기면 그만큼 늦게 끝난다(일의 양이 고정).
    private volatile long cpuLoops = env("CPU_LOOPS", 0);
    // 직렬 구간을 잠으로 채우면 도커 데스크톱 커널(고해상도 타이머 없음, HZ=1000)에서
    // 1ms 단위로 반올림돼 설정보다 0.7~1ms 길어진다. 그래서 기본은 CPU 를 돌려 정확히 채운다.
    // 락을 잡은 스레드 하나만 돌기 때문에 코어는 하나만 쓴다.
    private volatile boolean spinSerial = env("SPIN_SERIAL", 1) == 1;
    // 1 이면 병렬·직렬 구간의 길이를 설정값을 평균으로 하는 지수 분포에서 뽑는다.
    // 0 이면 매번 정확히 설정값만큼(결정적). 처리 시간이 흔들리는 시스템과 비교하려고 둔다.
    private volatile boolean expRandom = env("EXP_RANDOM", 0) == 1;

    @GetMapping("/work")
    public String work() {
        inFlight.incrementAndGet();
        try {
            if (parallelUs > 0) sleepUs(draw(parallelUs));
            if (cpuUs > 0) spinUs(cpuUs);
            if (cpuLoops > 0) burn(cpuLoops);

            long t0 = System.nanoTime();
            lock.lock();
            long t1 = System.nanoTime();
            try {
                int others = inFlight.get() - 1;            // 나를 뺀, 지금 서버 안에 있는 요청 수
                long hold = draw(serialUs) + coherencyUs * others;
                if (hold > 0) {
                    if (spinSerial) spinUs(hold); else sleepUs(hold);
                }
                peersSum.add(others);
            } finally {
                lock.unlock();
            }
            long t2 = System.nanoTime();
            lockWaitNs.add(t1 - t0);
            lockHoldNs.add(t2 - t1);
            count.increment();
        } finally {
            inFlight.decrementAndGet();
        }
        return "ok";
    }

    @PostMapping("/config")
    public Map<String, Long> config(@RequestParam(required = false) Long parallelUs,
                                    @RequestParam(required = false) Long serialUs,
                                    @RequestParam(required = false) Long coherencyUs,
                                    @RequestParam(required = false) Long cpuUs,
                                    @RequestParam(required = false) Long cpuLoops,
                                    @RequestParam(required = false) Boolean spinSerial,
                                    @RequestParam(required = false) Boolean expRandom) {
        if (parallelUs != null) this.parallelUs = parallelUs;
        if (serialUs != null) this.serialUs = serialUs;
        if (coherencyUs != null) this.coherencyUs = coherencyUs;
        if (cpuUs != null) this.cpuUs = cpuUs;
        if (cpuLoops != null) this.cpuLoops = cpuLoops;
        if (spinSerial != null) this.spinSerial = spinSerial;
        if (expRandom != null) this.expRandom = expRandom;
        return currentConfig();
    }

    /** 누적값. 측정 구간 앞뒤로 읽어 차이를 낸다. */
    @GetMapping("/stats")
    public Map<String, Object> stats() {
        Map<String, Object> m = new LinkedHashMap<>(currentConfig());
        m.put("count", count.sum());
        m.put("lockWaitNs", lockWaitNs.sum());
        m.put("lockHoldNs", lockHoldNs.sum());
        m.put("peersSum", peersSum.sum());
        m.put("cpus", (long) Runtime.getRuntime().availableProcessors());
        return m;
    }

    private Map<String, Long> currentConfig() {
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("parallelUs", parallelUs);
        m.put("serialUs", serialUs);
        m.put("coherencyUs", coherencyUs);
        m.put("cpuUs", cpuUs);
        m.put("cpuLoops", cpuLoops);
        m.put("spinSerial", spinSerial ? 1L : 0L);
        m.put("expRandom", expRandom ? 1L : 0L);
        return m;
    }

    private long draw(long meanUs) {
        if (!expRandom || meanUs <= 0) return meanUs;
        double u = java.util.concurrent.ThreadLocalRandom.current().nextDouble();
        return Math.round(-Math.log(1 - u) * meanUs);
    }

    /** parkNanos 는 일찍 깰 수 있어서 마감 시각까지 다시 잔다. */
    private static void sleepUs(long us) {
        long deadline = System.nanoTime() + us * 1_000;
        long left;
        while ((left = deadline - System.nanoTime()) > 0) {
            LockSupport.parkNanos(left);
        }
    }

    private static volatile long sink;

    private static void burn(long loops) {
        long x = 0;
        for (long i = 0; i < loops; i++) {
            x += x * 31 + i;
        }
        sink = x;
    }

    private static void spinUs(long us) {
        long deadline = System.nanoTime() + us * 1_000;
        long x = 0;
        while (System.nanoTime() < deadline) {
            x += x * 31 + 7;
        }
        sink = x;
    }

    private static long env(String name, long def) {
        String v = System.getenv(name);
        return v == null || v.isBlank() ? def : Long.parseLong(v);
    }
}
