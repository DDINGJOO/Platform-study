package lab.zc;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;

@Service
public class ReportService {

    // REPORT_IMPL=builder 로 띄우면 4절에서 프로파일을 보고 고친 구현을 쓴다. 기본은 처음 구현(format).
    private final boolean builder = "builder".equals(System.getenv("REPORT_IMPL"));

    /** 보고서 문자열. 줄마다 String.format 으로 새 문자열을 만들고, 마지막에 이어 붙인다. */
    public String render(int rows) {
        if (builder) {
            return renderWithBuilder(rows);
        }
        List<String> lines = new ArrayList<>();
        for (int i = 0; i < rows; i++) {
            lines.add(formatRow(i));
        }
        String out = "";
        for (String l : lines.subList(0, Math.min(lines.size(), 200))) {
            out = out + l;          // 반복 문자열 이어 붙이기: 매번 새 배열을 할당한다
        }
        return out + String.join("", lines);
    }

    String formatRow(int i) {
        return String.format("%08d|%-20s|%12.2f|%s%n", i, "item-" + i, i * 1.5, "x".repeat(64));
    }

    /** 같은 결과를 StringBuilder 하나에 직접 쓴다. 정규식으로 서식을 해석하지 않고, 중간 문자열도 만들지 않는다. */
    String renderWithBuilder(int rows) {
        StringBuilder head = new StringBuilder(200 * 128);
        StringBuilder all = new StringBuilder(rows * 128);
        for (int i = 0; i < rows; i++) {
            int start = all.length();
            appendRow(all, i);
            if (i < 200) {
                head.append(all, start, all.length());
            }
        }
        return head.append(all).toString();
    }

    static void appendRow(StringBuilder sb, int i) {
        String n = Integer.toString(i);
        for (int k = n.length(); k < 8; k++) sb.append('0');
        sb.append(n).append('|');
        String item = "item-" + i;
        sb.append(item);
        for (int k = item.length(); k < 20; k++) sb.append(' ');
        sb.append('|');
        long cents = Math.round(i * 150.0);   // i * 1.5 를 소수 둘째 자리까지
        String num = (cents / 100) + "." + (cents % 100 < 10 ? "0" : "") + (cents % 100);
        for (int k = num.length(); k < 12; k++) sb.append(' ');
        sb.append(num).append('|');
        sb.repeat('x', 64).append(System.lineSeparator());
    }
}
