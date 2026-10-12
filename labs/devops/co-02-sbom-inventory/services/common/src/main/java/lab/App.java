package lab;

import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class App {

    public static void main(String[] args) {
        SpringApplication.run(App.class, args);
    }

    /**
     * 정답지. 이 JVM 이 logback 클래스를 실제로 어느 jar 에서 읽었는지 돌려준다.
     * SBOM 도 빌드 파일도 아닌, 실행 중인 프로세스에게 직접 묻는 값이다.
     */
    @GetMapping("/lab/logback")
    public Map<String, String> logback() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("core", where("ch.qos.logback.core.CoreConstants"));
        m.put("classic", where("ch.qos.logback.classic.Logger"));
        return m;
    }

    private static String where(String className) {
        try {
            Class<?> c = Class.forName(className, false, App.class.getClassLoader());
            var src = c.getProtectionDomain().getCodeSource();
            return src == null ? "(unknown)" : src.getLocation().toString();
        } catch (ClassNotFoundException e) {
            return "none";
        }
    }
}
