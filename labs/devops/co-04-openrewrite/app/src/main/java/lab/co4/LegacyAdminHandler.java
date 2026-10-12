package lab.co4;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

class LegacyAdminHandler {
    private static final Logger log = LoggerFactory.getLogger(LegacyAdminHandler.class);

    String handle() {
        log.info("legacy admin page opened");                       // #S7 아무도 부르지 않는 경로
        return "legacy";
    }
}
