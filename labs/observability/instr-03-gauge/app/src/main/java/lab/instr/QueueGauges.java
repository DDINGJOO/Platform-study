package lab.instr;

import java.util.concurrent.atomic.AtomicInteger;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

// 같은 값(42)을 내는 게이지 다섯 개. 다른 점은 "누가 그 AtomicInteger 를 쥐고 있나" 하나다.
@RestController
public class QueueGauges {

    private final MeterRegistry registry;

    private final AtomicInteger held = new AtomicInteger(42);   // 이 빈의 필드가 쥔다

    QueueGauges(MeterRegistry registry) {
        this.registry = registry;
        // ① 지역 객체를 넘긴다. 생성자가 끝나면 아무도 강하게 쥐지 않는다
        AtomicInteger local = new AtomicInteger(42);
        Gauge.builder("queue.size", local, AtomicInteger::get)
                .tag("case", "local")
                .register(registry);

        // ② registry.gauge(...) 의 반환값을 버린다(2편 버그 코드와 같은 모양)
        registry.gauge("queue.size.shortcut", new AtomicInteger(42));

        // ③ 필드로 보관한다
        Gauge.builder("queue.size", held, AtomicInteger::get)
                .tag("case", "field")
                .register(registry);

        // ④ 지역 객체지만 strongReference(true)
        AtomicInteger strong = new AtomicInteger(42);
        Gauge.builder("queue.size", strong, AtomicInteger::get)
                .tag("case", "strong")
                .strongReference(true)
                .register(registry);

        // ⑤ Supplier 형태. 람다가 지역 객체를 붙잡는다
        AtomicInteger captured = new AtomicInteger(42);
        Gauge.builder("queue.size", captured::get)
                .tag("case", "supplier")
                .register(registry);
    }

    // 기동이 끝난 뒤에 ①과 같은 코드를 한 번 더 돈다. 기동 중 GC 에 휩쓸리지 않게 하려고 따로 뺐다
    @PostMapping("/register")
    String registerLate() {
        AtomicInteger local = new AtomicInteger(42);
        Gauge.builder("queue.size", local, AtomicInteger::get)
                .tag("case", "late-local")
                .register(registry);
        return "registered\n";
    }
}
