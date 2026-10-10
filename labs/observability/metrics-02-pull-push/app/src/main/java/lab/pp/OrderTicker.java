package lab.pp;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** 부하 도구 없이 지표가 계속 움직이게, 0.1초마다 주문 하나를 센다(초당 10건). */
@Component
public class OrderTicker {

    private final Counter orders;

    public OrderTicker(MeterRegistry registry) {
        this.orders = Counter.builder("shop.orders").register(registry);
    }

    @Scheduled(fixedRate = 100)
    public void tick() {
        orders.increment();
    }
}
