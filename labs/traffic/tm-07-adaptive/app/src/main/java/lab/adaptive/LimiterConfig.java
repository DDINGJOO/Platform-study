package lab.adaptive;

import com.netflix.concurrency.limits.Limit;
import com.netflix.concurrency.limits.limit.FixedLimit;
import com.netflix.concurrency.limits.limit.Gradient2Limit;
import com.netflix.concurrency.limits.limit.VegasLimit;
import com.netflix.concurrency.limits.limit.WindowedLimit;
import com.netflix.concurrency.limits.limiter.AbstractLimiter;
import com.netflix.concurrency.limits.limiter.SimpleLimiter;
import com.netflix.concurrency.limits.servlet.jakarta.ConcurrencyLimitServletFilter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * LAB_LIMITER 하나로 /work 앞에 무엇을 둘지 고른다.
 *   none      리미터 없음
 *   fixed     고정 한계 LAB_FIXED (기본 100). 사람이 정한 숫자 = 고정 벌크헤드와 같은 동작
 *   gradient2 Gradient2Limit 을 바로 건다. 요청 하나가 끝날 때마다 한계를 고친다. 라이브러리 기본값 그대로
 *   gradient2-windowed  WindowedLimit(Gradient2Limit). README 예시대로 1초 창의 평균으로 한계를 고친다. 기본값 그대로
 *   vegas     VegasLimit 을 바로 건다(SimpleLimiter 에 limit 을 안 주면 쓰이는 기본 알고리즘). 기본값 그대로
 * 한계를 넘으면 라이브러리 서블릿 필터가 기다리지 않고 429 를 돌려준다.
 */
@Configuration
public class LimiterConfig {

    private static final Logger log = LoggerFactory.getLogger(LimiterConfig.class);

    @Bean
    FilterRegistrationBean<ConcurrencyLimitServletFilter> limitFilter(
            @Value("${lab.limiter}") String kind, @Value("${lab.fixed}") int fixed,
            MeterRegistry meters, WorkController work) {
        var registry = new MicrometerMetricRegistry(meters);
        Gauge.builder("lab.pool.waiting", work, WorkController::waiting).register(meters);

        Limit limit = switch (kind) {
            case "none" -> null;
            case "fixed" -> FixedLimit.of(fixed);
            case "gradient2" -> Gradient2Limit.newBuilder().metricRegistry(registry).build();
            case "gradient2-windowed" -> WindowedLimit.newBuilder()
                    .build(Gradient2Limit.newBuilder().metricRegistry(registry).build());
            case "vegas" -> VegasLimit.newBuilder().metricRegistry(registry).build();
            default -> throw new IllegalArgumentException(kind);
        };
        log.info("limiter={} limit={}", kind, limit);
        if (limit == null) {
            var off = new FilterRegistrationBean<ConcurrencyLimitServletFilter>();
            off.setEnabled(false);
            off.setFilter(new ConcurrencyLimitServletFilter(SimpleLimiter.newBuilder().build()));
            return off;
        }
        AbstractLimiter<HttpServletRequest> limiter = SimpleLimiter.newBuilder()
                .named(kind.replace("-", "_"))
                .limit(limit)
                .metricRegistry(registry)
                .build();
        Gauge.builder("lab.limiter.inflight", limiter, AbstractLimiter::getInflight).register(meters);

        var bean = new FilterRegistrationBean<>(new ConcurrencyLimitServletFilter(limiter));
        bean.addUrlPatterns("/work");
        return bean;
    }
}
