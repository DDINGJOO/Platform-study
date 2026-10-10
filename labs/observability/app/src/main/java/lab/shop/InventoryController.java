package lab.shop;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@Profile("inventory")
@RestController
public class InventoryController {

    private static final Logger log = LoggerFactory.getLogger(InventoryController.class);
    private final JdbcTemplate jdbc;

    public InventoryController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/stock/{sku}")
    public Map<String, Object> stock(@PathVariable String sku,
                                     @RequestHeader(value = "traceparent", required = false) String traceparent) {
        // 앱은 이 헤더를 만들지 않았다. 호출한 쪽 에이전트가 붙여 보낸 것을 찍어 보기만 한다.
        log.info("traceparent={}", traceparent);
        Integer available = jdbc.queryForObject(
                "select available from stock where sku = ?", Integer.class, sku);
        return Map.of("sku", sku, "available", available);
    }
}
