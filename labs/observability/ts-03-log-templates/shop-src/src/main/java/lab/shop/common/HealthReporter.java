package lab.shop.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HealthReporter {
    private static final Logger log = LoggerFactory.getLogger(HealthReporter.class);

    public void heartbeat() {
        log.info("Heartbeat: uptime {} s, heap used {} MB of {} MB, threads {}", uptime, heapUsed, heapMax, threads);
    }

    public void gc(String collector, long pauseMs) {
        log.info("GC {} pause {} ms, freed {} MB", collector, pauseMs, freedMb);
    }

    public void sessionExpired(String user, String sessionId) {
        log.info("Session {} for user {} expired after {} minutes idle", sessionId, user, idleMinutes);
    }
}
