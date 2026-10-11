package lab.agg;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 엔드포인트 다섯 개(/api/checkout 등)가 각자 정해진 에러율과 지연으로 응답한다.
 * 대시보드에 선 다섯 개를 그리기 위한 앱이다. 지연은 base~2*base ms, 에러는 500.
 * 실행 중에 POST /admin/route?name=checkout&err=0.06&base=200 으로 바꿀 수 있다(장애 주입).
 */
@RestController
public class WorkController {

    record Route(double err, long baseMs) {}

    private final Map<String, Route> routes = new ConcurrentHashMap<>(Map.of(
            "checkout", new Route(0.004, 80),
            "order", new Route(0.003, 60),
            "search", new Route(0.002, 30),
            "cart", new Route(0.003, 40),
            "login", new Route(0.002, 50)));

    // 경로를 하나씩 적어야 uri 태그가 엔드포인트마다 달라진다. /api/{name} 으로 쓰면 uri 가 전부 "/api/{name}" 이 된다
    @GetMapping({"/api/checkout", "/api/order", "/api/search", "/api/cart", "/api/login"})
    public ResponseEntity<Map<String, Object>> call(HttpServletRequest req) throws InterruptedException {
        String name = req.getRequestURI().substring("/api/".length());
        Route r = routes.get(name);
        if (r == null) return ResponseEntity.notFound().build();
        ThreadLocalRandom rnd = ThreadLocalRandom.current();
        Thread.sleep(rnd.nextLong(r.baseMs(), r.baseMs() * 2));
        if (rnd.nextDouble() < r.err()) return ResponseEntity.status(500).body(Map.of("route", name, "ok", false));
        return ResponseEntity.ok(Map.of("route", name, "ok", true));
    }

    @PostMapping("/admin/route")
    public Map<String, Object> set(@RequestParam String name, @RequestParam double err, @RequestParam long base) {
        routes.put(name, new Route(err, base));
        return Map.of("route", name, "err", err, "base_ms", base);
    }
}
