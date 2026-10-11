package lab.adaptive;

import java.util.function.Supplier;

import com.netflix.concurrency.limits.MetricRegistry;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;

/**
 * concurrency-limits 가 내보내는 지표(limit, call, inflight, min_rtt …)를 Micrometer 로 옮긴다.
 * 라이브러리에는 Spectator 어댑터만 있어서 직접 만들었다. 이름 앞에 concurrency_limits 를 붙인다.
 * 분포(distribution)는 마지막 값을 게이지로도 남긴다. RTT 표본처럼 한 값을 그대로 보고 싶은 것이 많아서다.
 */
public class MicrometerMetricRegistry implements MetricRegistry {

    private final MeterRegistry meters;

    public MicrometerMetricRegistry(MeterRegistry meters) {
        this.meters = meters;
    }

    @Override
    public SampleListener distribution(String id, String... tags) {
        DistributionSummary summary = DistributionSummary.builder("concurrency_limits." + id).tags(tags).register(meters);
        var last = new java.util.concurrent.atomic.AtomicReference<Double>(Double.NaN);
        Gauge.builder("concurrency_limits." + id + ".last", last, r -> r.get()).tags(tags).register(meters);
        return value -> {
            summary.record(value.doubleValue());
            last.set(value.doubleValue());
        };
    }

    @Override
    public void gauge(String id, Supplier<Number> supplier, String... tags) {
        // 라이브러리는 this::getLimit 같은 메서드 참조를 넘긴다. Micrometer 게이지는 기본이 약한 참조라
        // 그대로 두면 GC 뒤 NaN 이 된다(README 함정). 강한 참조로 잡는다.
        Gauge.builder("concurrency_limits." + id, supplier, s -> s.get().doubleValue()).tags(Tags.of(tags))
                .strongReference(true).register(meters);
    }

    @Override
    public Counter counter(String id, String... tags) {
        io.micrometer.core.instrument.Counter c = io.micrometer.core.instrument.Counter.builder("concurrency_limits." + id).tags(tags).register(meters);
        return c::increment;
    }
}
