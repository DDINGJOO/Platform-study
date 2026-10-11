package lab.resil;

import java.net.http.HttpClient;
import java.time.Duration;

import io.github.resilience4j.bulkhead.BulkheadFullException;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 호출하는 쪽. /recommend 는 Guards 로 감싼 하위 호출, /pay 는 아무것도 감싸지 않은 하위 호출이다.
 * 거절 이유를 HTTP 상태로 구분한다: 429 = 비율 제한·벌크헤드, 503 = 서킷 OPEN, 502 = 하위 실패.
 */
@RestController
@Profile("caller")
public class CallerController {

    private final RestClient client;
    private final Guards guards;

    public CallerController(@Value("${lab.downstream}") String downstream, Guards guards) {
        var factory = new JdkClientHttpRequestFactory(
                HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build());
        factory.setReadTimeout(Duration.ofSeconds(3));
        this.client = RestClient.builder().baseUrl(downstream).requestFactory(factory).build();
        this.guards = guards;
    }

    @GetMapping("/recommend")
    public ResponseEntity<String> recommend() {
        try {
            String body = guards.wrap(() -> client.get().uri("/recommend").retrieve().body(String.class)).get();
            return ResponseEntity.ok(body);
        } catch (RequestNotPermitted | BulkheadFullException e) {
            return ResponseEntity.status(429).body(e.getClass().getSimpleName());
        } catch (CallNotPermittedException e) {
            return ResponseEntity.status(503).body("circuit open");
        } catch (RestClientException e) {
            return ResponseEntity.status(502).body(e.getClass().getSimpleName());
        }
    }

    @GetMapping("/pay")
    public String pay() {
        return client.get().uri("/pay").retrieve().body(String.class);
    }
}
