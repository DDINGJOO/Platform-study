package lab.adaptive;

import java.util.Map;
import java.util.concurrent.Semaphore;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * /work 는 "커넥션 40개짜리 하위 자원"을 하나 잡고 delayMs 동안 쓴다.
 * 자원이 모자라면 차례를 기다린다(공정 세마포어). 그래서 처리량 상한은 40 / delayMs 다.
 *   delayMs 50  → 초당 800건까지
 *   delayMs 500 → 초당 80건까지
 * 하위 지연 바꾸기: curl -X POST 'localhost:28281/admin/delay?ms=500'
 */
@RestController
public class WorkController {

    private final Semaphore pool = new Semaphore(Integer.getInteger("lab.pool", 40), true);
    private volatile long delayMs = 50;

    @GetMapping("/work")
    public String work() throws InterruptedException {
        pool.acquire();
        try {
            Thread.sleep(delayMs);
        } finally {
            pool.release();
        }
        return "ok";
    }

    @PostMapping("/admin/delay")
    public Map<String, Object> delay(@RequestParam long ms) {
        this.delayMs = ms;
        return Map.of("delayMs", ms);
    }

    public int waiting() {
        return pool.getQueueLength();
    }
}
