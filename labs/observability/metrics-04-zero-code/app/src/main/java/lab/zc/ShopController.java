package lab.zc;

import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ShopController {

    private final PriceService prices;
    private final ReportService reports;

    public ShopController(PriceService prices, ReportService reports) {
        this.prices = prices;
        this.reports = reports;
    }

    /** CPU 를 쓰는 엔드포인트. 할인 규칙을 상품마다 돌린다. */
    @GetMapping("/price/{sku}")
    public Map<String, Object> price(@PathVariable String sku, @RequestParam(defaultValue = "200") int items) {
        return Map.of("sku", sku, "total", prices.quote(sku, items));
    }

    /** 메모리를 많이 할당하는 엔드포인트. 보고서 문자열을 줄마다 새로 만든다. */
    @GetMapping("/report")
    public Map<String, Object> report(@RequestParam(defaultValue = "2000") int rows) {
        return Map.of("length", reports.render(rows).length());
    }

    /** 가끔 실패하는 엔드포인트. HTTP 지표의 오류 비율을 보려고 둔다. */
    @GetMapping("/checkout")
    public ResponseEntity<Map<String, Object>> checkout() {
        if (Math.random() < 0.1) {
            return ResponseEntity.status(503).body(Map.of("result", "unavailable"));
        }
        return ResponseEntity.ok(Map.of("result", "ok"));
    }
}
