package lab.slo;

import java.util.Map;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** 장애 주입 스위치. 예: curl -X POST 'localhost:24080/chaos?errorRate=0.05' */
@RestController
public class ChaosController {

    private final Chaos chaos;

    public ChaosController(Chaos chaos) {
        this.chaos = chaos;
    }

    @PostMapping("/chaos")
    public Map<String, Object> set(@RequestParam(required = false) Double errorRate,
                                   @RequestParam(required = false) Long latencyMs,
                                   @RequestParam(required = false) Integer allocMbPerSec,
                                   @RequestParam(required = false) Integer retainMb) {
        if (errorRate != null) chaos.errorRate = errorRate;
        if (latencyMs != null) chaos.latencyMs = latencyMs;
        if (allocMbPerSec != null) chaos.allocMbPerSec = allocMbPerSec;
        if (retainMb != null) chaos.retainMb = retainMb;
        return Map.of("errorRate", chaos.errorRate, "latencyMs", chaos.latencyMs,
                "allocMbPerSec", chaos.allocMbPerSec, "retainMb", chaos.retainMb,
                "retainedMbNow", chaos.retainedMb());
    }
}
