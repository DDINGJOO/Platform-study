package lab.instr;

import java.util.concurrent.ThreadLocalRandom;

import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.LongTaskTimer;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ReportController {

    private final Timer duration;          // 끝난 요청의 시간 (+ 서버 쪽 버킷)
    private final Timer durationPct;       // 같은 시간, 앱이 직접 계산한 백분위
    private final DistributionSummary rows;
    private final LongTaskTimer active;    // 아직 안 끝난 요청

    ReportController(MeterRegistry registry) {
        this.duration = Timer.builder("report.duration")
                .publishPercentileHistogram()           // 버킷을 내보낸다 → PromQL 로 백분위 계산
                .register(registry);
        this.durationPct = Timer.builder("report.duration.pct")
                .publishPercentiles(0.5, 0.99)          // 앱이 백분위를 계산해 값으로 내보낸다
                .register(registry);
        this.rows = DistributionSummary.builder("report.size")
                .baseUnit("rows")
                .register(registry);
        this.active = LongTaskTimer.builder("report.active")
                .register(registry);
    }

    // ms 동안 걸리는 보고서를 만든다
    @PostMapping("/reports")
    String report(@RequestParam long ms) {
        LongTaskTimer.Sample task = active.start();     // 시작하자마자 명부에 올라간다
        Timer.Sample sample = Timer.start();
        try {
            sleep(ms);
            int n = ThreadLocalRandom.current().nextInt(100, 5000);
            rows.record(n);
            return "rows=" + n + "\n";
        } finally {
            long nanos = sample.stop(duration);         // 끝나야 기록된다
            durationPct.record(nanos, java.util.concurrent.TimeUnit.NANOSECONDS);
            task.stop();                                // 명부에서 지운다
        }
    }

    // stop() 을 빼먹은 코드. 명부에 올라간 채로 영원히 남는다
    @PostMapping("/reports/leaky")
    String leaky() {
        active.start();
        return "started, never stopped\n";
    }

    private static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
