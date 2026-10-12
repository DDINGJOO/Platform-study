package lab.co4;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

class SearchHandler {
    private static final Logger log = LoggerFactory.getLogger(SearchHandler.class);
    static final String HELP = "call log.info(...) when you add a new query type";   // #G3 문자열
    private final AuditLogger logger = new AuditLogger();

    String handle(String q) {
        logger.info("search " + q);                                 // #G4 사내 AuditLogger.info
        return "results for " + q + " (" + logger.count() + ")";
    }

    String items(String q) {
        List<String> names = List.of("item-" + q, "item-" + q + "-2");
        names.forEach(log::info);                                   // #S8 메서드 참조
        return String.join(",", names);
    }
}
