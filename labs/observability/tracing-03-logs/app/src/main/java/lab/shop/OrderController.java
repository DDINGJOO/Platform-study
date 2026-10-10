package lab.shop;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

@Profile("order")
@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final RestClient inventory;
    private final RestClient payment;

    public OrderController(RestClient.Builder builder,
                           @Value("${shop.inventory-url}") String inventoryUrl,
                           @Value("${shop.payment-url}") String paymentUrl) {
        this.inventory = builder.clone().baseUrl(inventoryUrl).build();
        this.payment = builder.clone().baseUrl(paymentUrl).build();
    }

    public record OrderRequest(String sku, int qty) {}

    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> order(@RequestBody OrderRequest req) {
        Map<?, ?> stock = inventory.get().uri("/stock/{sku}", req.sku()).retrieve().body(Map.class);
        int available = ((Number) stock.get("available")).intValue();
        if (available < req.qty()) {
            log.info("재고 부족 sku={} available={}", req.sku(), available);
            return ResponseEntity.status(409).body(Map.of("result", "out_of_stock"));
        }
        try {
            payment.post().uri("/payments").body(Map.of("sku", req.sku(), "qty", req.qty()))
                    .retrieve().toBodilessEntity();
        } catch (RestClientResponseException e) {
            log.warn("결제 실패 sku={} status={}", req.sku(), e.getStatusCode().value());
            return ResponseEntity.status(502).body(Map.of("result", "payment_failed"));
        }
        log.info("주문 완료 sku={} qty={}", req.sku(), req.qty());
        return ResponseEntity.ok(Map.of("result", "ok"));
    }
}
