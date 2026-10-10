package lab.instr;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.composite.CompositeMeterRegistry;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final MeterRegistry registry;
    private final Timer checkout;
    private final DistributionSummary payload;

    // 주입받는 MeterRegistry 는 하나다. 어느 백엔드로 갈지는 이 코드가 모른다.
    OrderController(MeterRegistry registry) {
        this.registry = registry;
        this.checkout = Timer.builder("checkout.latency")
                .description("주문 처리 시간")
                .register(registry);
        this.payload = DistributionSummary.builder("order.payload")
                .baseUnit("bytes")
                .description("주문 요청 본문 크기")
                .register(registry);
    }

    @PostMapping("/orders")
    String order(@RequestParam(defaultValue = "seoul") String region) {
        Counter.builder("orders.created")
                .tag("region", region)
                .description("생성된 주문 수")
                .register(registry)
                .increment();
        long ms = ThreadLocalRandom.current().nextLong(20, 80);
        checkout.record(() -> sleep(ms));          // 실제로 20~80ms 걸리는 작업을 잰다
        payload.record(ThreadLocalRandom.current().nextInt(200, 1200));
        return "ok " + ms + "ms\n";
    }

    private static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    // 주입된 레지스트리가 실제로 무엇인지 확인하는 엔드포인트
    @GetMapping("/registries")
    String registries() {
        StringBuilder sb = new StringBuilder(registry.getClass().getName()).append('\n');
        if (registry instanceof CompositeMeterRegistry composite) {
            List<String> children = composite.getRegistries().stream()
                    .map(r -> "  └ " + r.getClass().getName())
                    .sorted().toList();
            children.forEach(c -> sb.append(c).append('\n'));
        }
        return sb.toString();
    }
}
