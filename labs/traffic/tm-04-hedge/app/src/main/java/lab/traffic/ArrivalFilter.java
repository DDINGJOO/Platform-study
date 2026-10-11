package lab.traffic;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** 요청 헤더가 도착한 순간을 남긴다. 본문을 읽기 전이라, 본문이 끝내 오지 않는 요청도 여기엔 찍힌다. */
@Component
public class ArrivalFilter extends OncePerRequestFilter {
    private static final Logger log = LoggerFactory.getLogger(ArrivalFilter.class);
    @Value("${LOG_ARRIVALS:false}") boolean logArrivals;

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        if (logArrivals && req.getRequestURI().equals("/work")) {
            log.info("head rid={} attempt={} method={} clen={}", req.getHeader("x-request-id"),
                    req.getHeader("x-envoy-attempt-count"), req.getMethod(), req.getHeader("content-length"));
        }
        try {
            chain.doFilter(req, res);
        } catch (IOException | RuntimeException e) {
            if (logArrivals) log.info("aborted rid={} attempt={} error={}", req.getHeader("x-request-id"),
                    req.getHeader("x-envoy-attempt-count"), e.getClass().getSimpleName());
            throw e;
        }
    }
}
