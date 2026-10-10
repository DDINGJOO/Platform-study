package lab.card;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 주문 한 건을 처리하는 척하고, 지표 두 개를 남긴다.
 *   shop.orders   카운터 (result 태그)
 *   shop.checkout 타이머 (result 태그)
 * LAB_USER_TAG 에 따라 user_id 태그가 붙는 자리가 달라진다. 실습은 이 값만 바꿔 가며 시계열 수를 센다.
 *   none      아무 데도 안 붙인다
 *   counter   카운터에만 붙인다
 *   timer     타이머에도 붙인다 (히스토그램 없음)
 *   histogram 타이머에도 붙이고, 히스토그램 버킷까지 켠다
 */
@RestController
public class CheckoutController {

    private final MeterRegistry registry;
    private final String userTag;

    public CheckoutController(MeterRegistry registry, @Value("${lab.user-tag}") String userTag) {
        this.registry = registry;
        this.userTag = userTag;
    }

    @GetMapping("/checkout")
    public Map<String, Object> checkout(@RequestParam String user) {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        long tookMs = 5 + r.nextLong(40);
        String result = r.nextDouble() < 0.05 ? "declined" : "ok";

        boolean tagCounter = !userTag.equals("none");
        boolean tagTimer = userTag.equals("timer") || userTag.equals("histogram");

        Counter.Builder orders = Counter.builder("shop.orders").tag("result", result);
        if (tagCounter) orders.tag("user_id", user);
        orders.register(registry).increment();

        Timer.Builder checkout = Timer.builder("shop.checkout").tag("result", result);
        if (tagTimer) checkout.tag("user_id", user);
        if (userTag.equals("histogram")) checkout.publishPercentileHistogram();
        checkout.register(registry).record(Duration.ofMillis(tookMs));

        return Map.of("user", user, "result", result, "tookMs", tookMs);
    }
}
