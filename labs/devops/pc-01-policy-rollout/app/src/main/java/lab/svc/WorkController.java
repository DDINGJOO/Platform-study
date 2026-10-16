package lab.svc;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Map;

import lab.platform.PlatformAutoConfiguration;
import lab.platform.PlatformHttp;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * GET /work 는 하위 서비스 /data 를 한 번 부르고 그 결과를 돌려준다.
 * 응답 헤더로 어느 정책이 적용됐는지 알린다: X-Policy(정책 이름), X-Attempts(시도 수), X-Starter(스타터 버전).
 *  - lib     : 스타터의 PlatformHttp(재시도·타임아웃 포함)
 *  - sidecar : 재시도 없는 클라이언트로 127.0.0.1:15001(옆 Envoy)을 부른다. 정책 헤더는 Envoy 가 붙여 준다
 */
@RestController
public class WorkController {

    private final String mode;
    private final String name;
    private final PlatformHttp platform;
    private final RestClient sidecar;

    public WorkController(@Value("${lab.mode}") String mode, @Value("${lab.name}") String name,
                          @Value("${lab.sidecar}") String sidecarUrl, PlatformHttp platform) {
        this.mode = mode;
        this.name = name;
        this.platform = platform;
        var factory = new JdkClientHttpRequestFactory(
                HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build());
        factory.setReadTimeout(Duration.ofSeconds(10));   // 정책은 Envoy 가 쥔다. 앱은 넉넉히 기다린다
        this.sidecar = RestClient.builder().baseUrl(sidecarUrl).requestFactory(factory).build();
    }

    @GetMapping("/work")
    public ResponseEntity<String> work() {
        if (mode.equals("sidecar")) return viaSidecar();
        PlatformHttp.Result r = platform.get("/data");
        return ResponseEntity.status(r.status())
                .header("X-Policy", r.policy())
                .header("X-Attempts", String.valueOf(r.attempts()))
                .header("X-Starter", PlatformAutoConfiguration.starterVersion())
                .header("X-Svc", name)
                .body(r.body());
    }

    private ResponseEntity<String> viaSidecar() {
        try {
            ResponseEntity<String> up = sidecar.get().uri("/data").retrieve().toEntity(String.class);
            return ResponseEntity.ok()
                    .header("X-Policy", h(up, "x-policy"))
                    .header("X-Attempts", h(up, "x-envoy-attempt-count"))
                    .header("X-Svc", name)
                    .body(up.getBody());
        } catch (HttpServerErrorException e) {
            var hs = e.getResponseHeaders();
            String policy = hs == null ? "?" : String.valueOf(hs.getFirst("x-policy"));
            String attempts = hs == null ? "?" : String.valueOf(hs.getFirst("x-envoy-attempt-count"));
            return ResponseEntity.status(502).header("X-Policy", policy).header("X-Attempts", attempts)
                    .header("X-Svc", name).body("downstream " + e.getStatusCode().value());
        } catch (ResourceAccessException e) {
            // 사이드카에 연결조차 못 했다(재기동 중 등)
            return ResponseEntity.status(503).header("X-Policy", "sidecar-down").header("X-Svc", name)
                    .body(e.getClass().getSimpleName());
        }
    }

    private static String h(ResponseEntity<?> r, String key) {
        String v = r.getHeaders().getFirst(key);
        return v == null ? "?" : v;
    }

    @GetMapping("/policy")
    public Map<String, Object> policy() {
        if (mode.equals("sidecar")) return Map.of("mode", mode, "svc", name);
        var p = platform.policy();
        return Map.of("mode", mode, "svc", name, "policy", p.name(), "maxAttempts", p.maxAttempts(),
                "timeoutMs", p.timeoutMs(), "starter", PlatformAutoConfiguration.starterVersion());
    }
}
