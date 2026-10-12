package lab.co4;

import org.slf4j.LoggerFactory;

class PaymentHandler {
    // SLF4J 인터페이스가 아니라 Logback 구현 타입으로 선언했다
    private final ch.qos.logback.classic.Logger log =
        (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(PaymentHandler.class);
    // 이름이 logger 인 JUL 로거
    private final java.util.logging.Logger logger = java.util.logging.Logger.getLogger("payments");

    String handle(String id) {
        log.info("payment {}", id);                                 // #S5 Logback 타입으로 부름
        logger.info("jul payment " + id);                           // #G2 JUL Logger.info
        LoggerFactory.getLogger(PaymentHandler.class).info("inline {}", id);   // #S6 변수 없이 바로
        return "paid " + id;
    }
}
