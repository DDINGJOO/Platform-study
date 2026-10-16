package lab.ts01;

import java.util.List;
import java.util.Map;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    // exact: 고객 코드를 그대로 비교한다. (customer_ref, created_at) 인덱스를 탄다.
    static final String EXACT = """
            select id, amount, created_at from orders
            where customer_ref = ?
            order by created_at desc limit 20""";

    // ci: "고객 코드 대소문자 무시" 요구로 바꾼 쿼리. 컬럼에 lower() 를 씌워서 인덱스를 못 탄다.
    static final String CASE_INSENSITIVE = """
            select id, amount, created_at from orders
            where lower(customer_ref) = lower(?)
            order by created_at desc limit 20""";

    private final JdbcTemplate jdbc;
    private final String sql;
    private final String banner;

    public OrderController(JdbcTemplate jdbc, MeterRegistry registry,
                           @Value("${shop.query-variant:exact}") String variant,
                           @Value("${shop.banner:}") String banner,
                           @Value("${shop.version:dev}") String version) {
        this.jdbc = jdbc;
        this.sql = "ci".equals(variant) ? CASE_INSENSITIVE : EXACT;
        this.banner = banner;
        // 지금 떠 있는 버전과 설정을 지표로 남긴다. 값은 늘 1이고 라벨이 정보다.
        Gauge.builder("shop.build.info", () -> 1)
                .tags("version", version, "query", variant, "banner", banner)
                .register(registry);
    }

    @GetMapping("/orders/recent")
    public Map<String, Object> recent(@RequestParam String customer) {
        List<Map<String, Object>> rows = jdbc.queryForList(sql, customer);
        return Map.of("customer", customer, "count", rows.size(), "banner", banner);
    }
}
