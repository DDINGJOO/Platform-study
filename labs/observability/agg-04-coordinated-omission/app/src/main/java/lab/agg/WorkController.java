package lab.agg;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 2~4ms 동안 자고 돌아오는 엔드포인트. 앱 자체에는 멈춤이 없다.
 * 멈춤은 밖에서 넣는다: scripts/pause-loop.sh 가 컨테이너를 docker pause 로 얼린다(프로세스 전체 정지).
 * 지연은 스프링이 자동으로 거는 http.server.requests 타이머가 잰다(application.yml 에서 버킷을 켰다).
 */
@RestController
public class WorkController {

    @GetMapping("/work")
    public Map<String, Object> work() throws InterruptedException {
        long ms = ThreadLocalRandom.current().nextLong(2, 5);
        Thread.sleep(ms);
        return Map.of("slept_ms", ms);
    }
}
