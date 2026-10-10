package lab.shop;

import java.io.IOException;
import java.util.stream.Collectors;

import io.opentelemetry.api.baggage.Baggage;
import io.opentelemetry.api.trace.Span;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 결제 서비스의 실패 주입 지점. 요청에 실려 온 baggage 에 chaos 깃발이 있을 때만 발화한다.
 *   chaos=payment-fail : 결제를 503 으로 실패시킨다
 *   chaos=payment-slow : 결제를 2초 늦춘다
 * baggage 는 이 앱이 읽지 않았다. 에이전트가 들어온 헤더를 풀어 현재 컨텍스트에 넣어 둔 것을 꺼내기만 한다.
 */
@Profile("payment")
@Component
class ChaosFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(ChaosFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        Baggage baggage = Baggage.current();
        if (!baggage.isEmpty()) {
            String all = baggage.asMap().entrySet().stream()
                    .map(e -> e.getKey() + "=" + e.getValue().getValue())
                    .collect(Collectors.joining(","));
            log.info("받은 baggage {}건, {}바이트: {}", baggage.size(), all.length(),
                    all.length() > 120 ? all.substring(0, 120) + "..." : all);
        }
        String flag = baggage.getEntryValue("chaos");
        if (flag != null) {
            Span.current().setAttribute("chaos.flag", flag);
        }
        if ("payment-fail".equals(flag)) {
            Span.current().setAttribute("chaos.injected", true);
            log.warn("chaos 깃발로 결제 실패를 주입한다");
            res.setStatus(503);
            res.getWriter().write("{\"result\":\"chaos\"}");
            return;
        }
        if ("payment-slow".equals(flag)) {
            Span.current().setAttribute("chaos.injected", true);
            try {
                Thread.sleep(2000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        chain.doFilter(req, res);
    }
}
