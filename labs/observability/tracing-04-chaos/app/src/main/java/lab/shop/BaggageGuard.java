package lab.shop;

import java.io.IOException;

import io.opentelemetry.api.baggage.Baggage;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 입구(주문) 서비스의 baggage 검문. 바깥에서 온 chaos 깃발은 토큰이 맞을 때만 통과시키고,
 * 아니면 깃발을 뺀 baggage 로 바꿔 끼운 채 다음으로 넘긴다. 하위 호출은 바꿔 끼운 baggage 를 싣고 나간다.
 * SHOP_BAGGAGE_GUARD=false(기본)이면 아무것도 하지 않는다.
 */
@Profile("order")
@Component
class BaggageGuard extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(BaggageGuard.class);

    private final boolean enabled;
    private final String token;

    BaggageGuard(@Value("${shop.baggage-guard}") boolean enabled, @Value("${shop.chaos-token}") String token) {
        this.enabled = enabled;
        this.token = token;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        Baggage baggage = Baggage.current();
        String flag = baggage.getEntryValue("chaos");
        boolean trusted = !token.isEmpty() && token.equals(req.getHeader("X-Chaos-Token"));
        if (!enabled || flag == null || trusted) {
            chain.doFilter(req, res);
            return;
        }
        Span.current().setAttribute("chaos.rejected", flag);
        log.warn("토큰 없는 chaos 깃발을 버린다: {}", flag);
        Baggage cleaned = baggage.toBuilder().remove("chaos").build();
        try (Scope ignored = Context.current().with(cleaned).makeCurrent()) {
            chain.doFilter(req, res);
        }
    }
}
