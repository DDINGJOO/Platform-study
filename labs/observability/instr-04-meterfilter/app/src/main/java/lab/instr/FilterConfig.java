package lab.instr;

import java.util.concurrent.atomic.AtomicLong;

import io.micrometer.core.instrument.FunctionCounter;
import io.micrometer.core.instrument.Meter;
import io.micrometer.core.instrument.binder.MeterBinder;
import io.micrometer.core.instrument.config.MeterFilter;
import io.micrometer.core.instrument.config.MeterFilterReply;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;

// 스프링 부트는 MeterFilter 빈을 모아 미터가 만들어지기 전에 레지스트리에 건다.
// 여러 개면 @Order 순서대로 걸린다.
@Configuration(proxyBeanMethods = false)
class FilterConfig {

    // 상한에 걸려 버려진 횟수. 버려진 걸 버려졌다고 알려 주는 메타 지표용
    static final AtomicLong DENIED = new AtomicLong();

    // ① 거부: user_id 태그가 붙은 미터는 받지 않는다
    @Bean
    @Order(1)
    MeterFilter denyUserId() {
        return MeterFilter.deny(id -> id.getTag("user_id") != null);
    }

    // ② 이름 바꾸기: login 미터의 uid 태그를 user_id 로 바꾼다. 거부(①)보다 뒤에 걸었다
    @Bean
    @Order(2)
    MeterFilter renameUid() {
        return MeterFilter.renameTag("login", "uid", "user_id");
    }

    // ③ 통과: vip- 로 시작하는 상품은 상한과 상관없이 받는다. 상한(④)보다 앞에 둔다
    @Bean
    @Order(3)
    MeterFilter acceptVip() {
        return MeterFilter.accept(id -> id.getName().equals("item.views")
                && id.getTag("item") != null && id.getTag("item").startsWith("vip-"));
    }

    // ④ 상한: item.views 의 item 태그 값은 50가지까지. 넘치면 거부하면서 횟수를 센다
    @Bean
    @Order(4)
    MeterFilter capItems() {
        MeterFilter denyAndCount = new MeterFilter() {
            @Override
            public MeterFilterReply accept(Meter.Id id) {
                DENIED.incrementAndGet();
                return MeterFilterReply.DENY;
            }
        };
        return MeterFilter.maximumAllowableTags("item.views", "item", 50, denyAndCount);
    }

    @Bean
    MeterBinder deniedMeter() {
        return registry -> FunctionCounter.builder("meter.filter.denied", DENIED, AtomicLong::get)
                .description("상한 필터가 거부한 미터 등록 시도")
                .register(registry);
    }
}
