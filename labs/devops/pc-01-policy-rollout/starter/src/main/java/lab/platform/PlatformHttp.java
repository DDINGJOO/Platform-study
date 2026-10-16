package lab.platform;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * 재시도·타임아웃이 걸린 하위 호출. 정책이 바뀌면 클라이언트와 Retry 를 통째로 새로 만들어 바꿔 끼운다.
 * 응답에 어떤 정책으로 몇 번 시도했는지 실어 보낸다(관측용).
 */
public class PlatformHttp {

    public record Result(int status, String body, String policy, int attempts) {}

    private record Wiring(CallPolicy policy, RestClient client, Retry retry) {}

    private final String baseUrl;
    private final AtomicReference<Wiring> wiring = new AtomicReference<>();

    public PlatformHttp(String baseUrl, CallPolicy initial) {
        this.baseUrl = baseUrl;
        apply(initial);
    }

    public CallPolicy policy() {
        return wiring.get().policy();
    }

    public final void apply(CallPolicy p) {
        var factory = new JdkClientHttpRequestFactory(
                HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build());
        factory.setReadTimeout(Duration.ofMillis(p.timeoutMs()));
        RestClient client = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
        // Envoy 의 기본 재시도 간격(25ms 기준 지수 백오프)과 비슷하게 25ms 고정 대기.
        Retry retry = Retry.of("downstream", RetryConfig.custom()
                .maxAttempts(p.maxAttempts())
                .waitDuration(Duration.ofMillis(25))
                .retryExceptions(HttpServerErrorException.class, ResourceAccessException.class)
                .build());
        wiring.set(new Wiring(p, client, retry));
    }

    public Result get(String path) {
        Wiring w = wiring.get();
        AtomicInteger attempts = new AtomicInteger();
        try {
            String body = Retry.decorateSupplier(w.retry(), () -> {
                attempts.incrementAndGet();
                return w.client().get().uri(path).retrieve().body(String.class);
            }).get();
            return new Result(200, body, w.policy().name(), attempts.get());
        } catch (HttpServerErrorException e) {
            return new Result(502, "downstream " + e.getStatusCode().value(), w.policy().name(), attempts.get());
        } catch (ResourceAccessException e) {
            return new Result(504, "downstream timeout", w.policy().name(), attempts.get());
        }
    }
}
