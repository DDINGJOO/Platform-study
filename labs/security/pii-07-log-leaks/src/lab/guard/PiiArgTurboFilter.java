package lab.guard;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.turbo.TurboFilter;
import ch.qos.logback.core.spi.FilterReply;
import java.lang.reflect.Field;
import java.lang.reflect.RecordComponent;
import org.slf4j.LoggerFactory;
import org.slf4j.Marker;
import lab.Pii;

/**
 * 로그 인자 가운데 @Pii 필드를 가진 객체가 있으면 그 줄을 통째로 버린다.
 * TurboFilter 는 이벤트가 만들어지기 전에 불려 형식 문자열과 인자를 본다. 고쳐 쓸 수는 없고 통과·거부만 고른다.
 */
public class PiiArgTurboFilter extends TurboFilter {
    private static final org.slf4j.Logger GUARD = LoggerFactory.getLogger("pii-guard");
    private boolean enabled;
    public void setEnabled(boolean v) { this.enabled = v; }

    @Override
    public FilterReply decide(Marker marker, Logger logger, Level level, String format, Object[] params, Throwable t) {
        if (!enabled || params == null || "pii-guard".equals(logger.getName())) return FilterReply.NEUTRAL;
        for (Object p : params) {
            if (p != null && hasPii(p.getClass())) {
                GUARD.warn("@Pii 객체를 인자로 받은 로그를 버림: logger={} format=\"{}\" type={}",
                        logger.getName(), format, p.getClass().getSimpleName());
                return FilterReply.DENY;
            }
        }
        return FilterReply.NEUTRAL;
    }

    static boolean hasPii(Class<?> c) {
        if (c.isRecord()) {
            for (RecordComponent rc : c.getRecordComponents()) if (rc.isAnnotationPresent(Pii.class)) return true;
        }
        for (Class<?> k = c; k != null && k != Object.class; k = k.getSuperclass()) {
            for (Field f : k.getDeclaredFields()) if (f.isAnnotationPresent(Pii.class)) return true;
        }
        return false;
    }
}
