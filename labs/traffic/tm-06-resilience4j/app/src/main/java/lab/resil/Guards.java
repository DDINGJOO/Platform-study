package lab.resil;

import java.time.Duration;
import java.util.function.Supplier;

import io.github.resilience4j.bulkhead.Bulkhead;
import io.github.resilience4j.bulkhead.BulkheadConfig;
import io.github.resilience4j.bulkhead.BulkheadFullException;
import io.github.resilience4j.bulkhead.BulkheadRegistry;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.micrometer.tagged.TaggedBulkheadMetrics;
import io.github.resilience4j.micrometer.tagged.TaggedCircuitBreakerMetrics;
import io.github.resilience4j.micrometer.tagged.TaggedRateLimiterMetrics;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * 호출하는 쪽(order)이 하위 호출을 감싸는 방법을 PATTERN 하나로 고른다.
 * 스프링 부트 스타터 없이 코어 API 로 직접 만든다. 숫자는 README 와 글에 적은 그대로다.
 */
@Component
@Profile("caller")
public class Guards {

    private static final Logger log = LoggerFactory.getLogger(Guards.class);
    private final String pattern;
    private final RateLimiter rateLimiter;
    private final Bulkhead bulkhead;
    private final CircuitBreaker circuitBreaker;

    public Guards(@Value("${lab.pattern}") String pattern,
                  @Value("${lab.cb-ignore-bulkhead:false}") boolean ignoreBulkheadFull,
                  MeterRegistry meters) {
        this.pattern = pattern;

        // 1초마다 허가 30개. 기다리지 않는다(timeoutDuration 0).
        RateLimiterRegistry rl = RateLimiterRegistry.of(RateLimiterConfig.custom()
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .limitForPeriod(30)
                .timeoutDuration(Duration.ZERO)
                .build());
        // 동시에 10개까지. 자리가 없으면 바로 거절(maxWaitDuration 0, 기본값).
        BulkheadRegistry bh = BulkheadRegistry.of(BulkheadConfig.custom()
                .maxConcurrentCalls(10)
                .maxWaitDuration(Duration.ZERO)
                .build());
        // 최근 20건 중 10건 이상 쌓이면 판정, 실패율 50% 이상이면 OPEN, 10초 뒤 HALF_OPEN 에서 5건 시험.
        // 어떤 예외를 실패로 셀지는 정하지 않았다(기본: 모든 예외가 실패).
        CircuitBreakerConfig.Builder cbConfig = CircuitBreakerConfig.custom()
                .slidingWindowType(SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(20)
                .minimumNumberOfCalls(10)
                .failureRateThreshold(50)
                .waitDurationInOpenState(Duration.ofSeconds(10))
                .permittedNumberOfCallsInHalfOpenState(5);
        // LAB_CB_IGNORE_BULKHEAD=true 면 우리 쪽 벌크헤드 거절은 실패율에 넣지 않는다.
        if (ignoreBulkheadFull) cbConfig.ignoreExceptions(BulkheadFullException.class);
        CircuitBreakerRegistry cb = CircuitBreakerRegistry.of(cbConfig.build());

        this.rateLimiter = rl.rateLimiter("recommend");
        this.bulkhead = bh.bulkhead("recommend");
        this.circuitBreaker = cb.circuitBreaker("recommend");

        // 이 패턴에서 실제로 쓰는 것만 지표로 등록한다.
        if (pattern.equals("ratelimiter")) TaggedRateLimiterMetrics.ofRateLimiterRegistry(rl).bindTo(meters);
        if (pattern.equals("bulkhead") || pattern.equals("cb-over-bulkhead")) TaggedBulkheadMetrics.ofBulkheadRegistry(bh).bindTo(meters);
        if (pattern.equals("circuitbreaker") || pattern.equals("cb-over-bulkhead")) TaggedCircuitBreakerMetrics.ofCircuitBreakerRegistry(cb).bindTo(meters);

        circuitBreaker.getEventPublisher().onStateTransition(e ->
                log.info("circuit {} {}", e.getStateTransition(), circuitBreaker.getMetrics().getFailureRate()));
        log.info("pattern={} cbIgnoreBulkhead={}", pattern, ignoreBulkheadFull);
    }

    public <T> Supplier<T> wrap(Supplier<T> call) {
        return switch (pattern) {
            case "ratelimiter" -> RateLimiter.decorateSupplier(rateLimiter, call);
            case "bulkhead" -> Bulkhead.decorateSupplier(bulkhead, call);
            case "circuitbreaker" -> CircuitBreaker.decorateSupplier(circuitBreaker, call);
            // 스프링 부트 애너테이션 기본 순서처럼 서킷 브레이커가 벌크헤드를 감싼다.
            case "cb-over-bulkhead" -> CircuitBreaker.decorateSupplier(circuitBreaker,
                    Bulkhead.decorateSupplier(bulkhead, call));
            case "none" -> call;
            default -> throw new IllegalArgumentException(pattern);
        };
    }
}
