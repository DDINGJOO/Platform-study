package lab.shop.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DataSourceMonitor {
    private static final Logger log = LoggerFactory.getLogger(DataSourceMonitor.class);

    public void report(PoolStats s) {
        log.debug("Pool stats: active={} idle={} waiting={} max={}", s.active(), s.idle(), s.waiting(), s.max());
    }

    public void exhausted(PoolStats s) {
        log.warn("Connection is not available, request timed out after {} ms (total={}, active={}, idle={}, waiting={})", s.timeoutMs(), s.max(), s.active(), s.idle(), s.waiting());
    }
}
