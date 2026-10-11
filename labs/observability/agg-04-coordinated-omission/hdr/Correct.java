import java.io.BufferedReader;
import java.nio.file.Files;
import java.nio.file.Path;

import org.HdrHistogram.Histogram;

/**
 * k6 CSV 의 http_req_duration 을 HdrHistogram 에 넣고 백분위를 찍는다.
 *   raw       : recordValue(v)                                (보정 없음)
 *   at-record : recordValueWithExpectedInterval(v, interval)  (기록하면서 보정)
 *   post      : raw.copyCorrectedForCoordinatedOmission(interval) (다 기록한 뒤 보정)
 * 사용: java -cp HdrHistogram.jar Correct.java <k6.csv> <예상 간격 ms>
 * 값은 마이크로초로 기록한다(유효숫자 3자리).
 */
public class Correct {
    public static void main(String[] args) throws Exception {
        Path csv = Path.of(args[0]);
        long intervalUs = Math.round(Double.parseDouble(args[1]) * 1000);
        Histogram raw = new Histogram(3_600_000_000L, 3);
        Histogram atRecord = new Histogram(3_600_000_000L, 3);
        try (BufferedReader r = Files.newBufferedReader(csv)) {
            String line = r.readLine(); // 머리줄
            while ((line = r.readLine()) != null) {
                if (!line.startsWith("http_req_duration,")) continue;
                String[] f = line.split(",", 4);
                long us = Math.round(Double.parseDouble(f[2]) * 1000);
                raw.recordValue(us);
                atRecord.recordValueWithExpectedInterval(us, intervalUs);
            }
        }
        Histogram post = raw.copyCorrectedForCoordinatedOmission(intervalUs);
        System.out.printf("%s  예상 간격 %s ms%n", csv.getFileName(), args[1]);
        System.out.printf("%-10s %9s %9s %9s %9s %9s %9s%n", "", "건수", "p50", "p90", "p99", "p99.9", "max");
        print("raw", raw);
        print("at-record", atRecord);
        print("post", post);
    }

    static void print(String name, Histogram h) {
        System.out.printf("%-10s %9d %9s %9s %9s %9s %9s%n", name, h.getTotalCount(),
                ms(h.getValueAtPercentile(50)), ms(h.getValueAtPercentile(90)),
                ms(h.getValueAtPercentile(99)), ms(h.getValueAtPercentile(99.9)), ms(h.getMaxValue()));
    }

    static String ms(long us) {
        return us >= 100_000 ? String.format("%.0fms", us / 1000.0) : String.format("%.2fms", us / 1000.0);
    }
}
