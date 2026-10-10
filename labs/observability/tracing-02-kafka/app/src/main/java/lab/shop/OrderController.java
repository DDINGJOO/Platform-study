package lab.shop;

import java.util.Map;
import java.util.UUID;

import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@Profile("order")
@RestController
public class OrderController {

    private final KafkaTemplate<String, String> kafka;

    public OrderController(KafkaTemplate<String, String> kafka) {
        this.kafka = kafka;
    }

    public record OrderRequest(String sku, int qty) {}

    // 주문을 받으면 결제를 HTTP 로 부르지 않고 orders 토픽에 넣고 바로 202 를 돌려준다.
    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> order(@RequestBody OrderRequest req) throws Exception {
        String orderId = UUID.randomUUID().toString();
        String payload = orderId + "," + req.sku() + "," + req.qty();
        kafka.send("orders", orderId, payload).get();   // 브로커가 받았다고 답할 때까지 기다린다
        return ResponseEntity.accepted().body(Map.of("orderId", orderId));
    }
}
