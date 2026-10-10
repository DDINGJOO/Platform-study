package lab.instr;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.config.MeterFilter;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

@RestController
public class ItemController {

    private final MeterRegistry registry;
    private final RestClient client;

    ItemController(MeterRegistry registry, RestClient.Builder builder) {
        this.registry = registry;
        this.client = builder.baseUrl("http://localhost:8080").build();
    }

    // 상품 조회. 상품 ID 를 그대로 태그에 넣는다(고카디널리티)
    @GetMapping("/items/{id}")
    String view(@PathVariable String id) {
        Counter.builder("item.views").tag("item", id).register(registry).increment();
        return id + "\n";
    }

    // 자기 자신의 /items/{id} 를 n 번 부른다. URI 를 문자열로 이어 붙였다(템플릿 없음)
    @PostMapping("/fanout")
    String fanout(@RequestParam int n, @RequestParam(defaultValue = "") String prefix) {
        for (int i = 0; i < n; i++) {
            client.get().uri("/items/" + prefix + i).retrieve().toBodilessEntity();
        }
        return "called " + n + "\n";
    }

    // 로그인. uid 태그를 단다. 필터 ②가 user_id 로 바꾸고, 필터 ①이 그걸 거부할까?
    @PostMapping("/login")
    String login(@RequestParam String uid) {
        Counter.builder("login").tag("uid", uid).register(registry).increment();
        return "login " + uid + "\n";
    }

    // 기동이 끝난 뒤에 필터를 하나 더 건다(하지 말아야 할 일)
    @PostMapping("/late-filter")
    String lateFilter() {
        registry.config().meterFilter(MeterFilter.denyNameStartsWith("item.views"));
        return "late filter added\n";
    }
}
