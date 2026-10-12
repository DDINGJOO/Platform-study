package lab.co3.audit;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class AuditApp {
    public static void main(String[] args) { SpringApplication.run(AuditApp.class, args); }

    private final AuditLogRepository audits;

    public AuditApp(AuditLogRepository audits) { this.audits = audits; }

    /** 공개 API 는 이것 하나다. 감사 로그는 내부에서만 쓴다. */
    @PostMapping("/orders")
    public String order() {
        audits.save(new AuditLog("order-created"));
        return "ok";
    }

    @Bean
    CommandLineRunner seed() {
        return args -> {
            audits.save(new AuditLog("admin-login"));
            audits.save(new AuditLog("password-reset"));
            audits.save(new AuditLog("refund-approved"));
        };
    }
}
