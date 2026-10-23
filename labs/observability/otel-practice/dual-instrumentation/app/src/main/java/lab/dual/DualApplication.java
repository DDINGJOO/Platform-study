package lab.dual;

import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import java.util.LinkedHashMap;
import java.util.Map;

@SpringBootApplication
@RestController
public class DualApplication {
    private static final Logger log = LoggerFactory.getLogger(DualApplication.class);
    private final RestClient client;
    private final ObservationRegistry observations;
    public DualApplication(RestClient.Builder builder, ObservationRegistry observations) {
        this.client = builder.baseUrl("http://localhost:8080").build();
        this.observations = observations;
    }
    public static void main(String[] args) { SpringApplication.run(DualApplication.class, args); }
    @GetMapping("/ready")
    Map<String, String> ready() { return Map.of("status", "UP"); }
    @GetMapping("/checkout")
    Map<String, Object> checkout(@RequestParam String request) {
        return Observation.createNotStarted("checkout.quote", observations)
            .lowCardinalityKeyValue("lab.operation", "quote")
            .highCardinalityKeyValue("lab.request", request)
            .observe(() -> {
                Map<String, Object> result = context("checkout", request);
                result.put("child", client.get().uri("/inventory?request={request}", request).retrieve().body(Map.class));
                log.info("CHECKOUT request={} result=ok", request);
                return result;
            });
    }
    @GetMapping("/inventory")
    Map<String, Object> inventory(@RequestParam String request,
            @RequestHeader(value="traceparent", defaultValue="absent") String traceparent) {
        Map<String, Object> result = context("inventory", request);
        result.put("receivedTraceparent", traceparent);
        return result;
    }
    private Map<String, Object> context(String stage, String request) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("stage", stage);
        result.put("request", request);
        for (String key : new String[]{"traceId", "spanId", "trace_id", "span_id"}) {
            result.put(key, MDC.get(key) == null ? "empty" : MDC.get(key));
        }
        log.info("LAB stage={} request={}", stage, request);
        return result;
    }
}
