package lab.platform;

import java.io.IOException;
import java.io.InputStream;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** 하위 호출 정책. maxAttempts 는 첫 시도를 포함한 횟수(1 = 재시도 없음), timeoutMs 는 시도 하나의 읽기 타임아웃. */
public record CallPolicy(String name, int maxAttempts, long timeoutMs) {

    static CallPolicy from(Properties p) {
        return new CallPolicy(p.getProperty("policy.name"),
                Integer.parseInt(p.getProperty("policy.maxAttempts")),
                Long.parseLong(p.getProperty("policy.timeoutMs")));
    }

    /** jar 에 구워진 기본값. */
    static Properties bundled() {
        try (InputStream in = CallPolicy.class.getResourceAsStream("/platform-defaults.properties")) {
            Properties p = new Properties();
            p.load(in);
            return p;
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    /** 실행 중에 읽는 파일. 없는 키는 기본값을 쓴다. */
    static CallPolicy fromFile(Path file, Properties defaults) throws IOException {
        Properties p = new Properties();
        p.putAll(defaults);
        try (Reader r = Files.newBufferedReader(file)) {
            p.load(r);
        }
        return from(p);
    }
}
