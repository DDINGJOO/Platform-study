package lab.platform;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;

/**
 * 스타터를 의존성에 넣기만 하면 PlatformHttp 빈이 생긴다.
 * 기본: jar 에 구워진 정책(platform-defaults.properties). 바꾸려면 스타터 새 버전 → 서비스 재빌드 → 재기동.
 * platform.policy-file 을 주면 그 파일을 1초마다 읽어 정책을 바꿔 끼운다(재기동 없이).
 */
@AutoConfiguration
public class PlatformAutoConfiguration {

    private static final Logger log = LoggerFactory.getLogger(PlatformAutoConfiguration.class);

    @Bean
    @ConditionalOnMissingBean
    public PlatformHttp platformHttp(@Value("${platform.downstream}") String downstream,
                                     @Value("${platform.policy-file:}") String policyFile) throws Exception {
        Properties defaults = CallPolicy.bundled();
        CallPolicy initial = CallPolicy.from(defaults);
        PlatformHttp http = new PlatformHttp(downstream, initial);
        log.info("platform-starter {} policy={}", defaults.getProperty("starter.version"), initial);

        if (!policyFile.isBlank()) {
            Path file = Path.of(policyFile);
            if (Files.exists(file)) http.apply(CallPolicy.fromFile(file, defaults));
            var timer = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "policy-watch");
                t.setDaemon(true);
                return t;
            });
            timer.scheduleWithFixedDelay(() -> {
                try {
                    if (!Files.exists(file)) return;
                    CallPolicy next = CallPolicy.fromFile(file, defaults);
                    if (!next.equals(http.policy())) {
                        http.apply(next);
                        log.info("policy changed {}", next);
                    }
                } catch (Exception e) {
                    log.warn("policy file unreadable, keeping {}: {}", http.policy(), e.toString());
                }
            }, 1, 1, TimeUnit.SECONDS);
        }
        return http;
    }

    public static String starterVersion() {
        return CallPolicy.bundled().getProperty("starter.version");
    }
}
