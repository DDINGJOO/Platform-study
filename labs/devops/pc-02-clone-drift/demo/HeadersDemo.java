// 묶음 124: HttpHeaders 의 위임 메서드 블록과 WebSocketHttpHeaders 의 같은 블록.
// 2024-05-24 커밋 903493e9a9 가 HttpHeaders(와 ReadOnlyHttpHeaders)에만 asSingleValueMap() 위임을 넣었다.
// WebSocketHttpHeaders 는 자기 필드(headers)에 위임하는데, 이 메서드는 덮어쓰지 않아 부모의 빈 맵을 본다.
//   java -cp "$WORK/jars/6.2.0/*" demo/HeadersDemo.java
import org.springframework.http.HttpHeaders;
import org.springframework.web.socket.WebSocketHttpHeaders;

public class HeadersDemo {
    public static void main(String[] args) {
        System.out.println("spring-web " + HttpHeaders.class.getPackage().getImplementationVersion());
        HttpHeaders plain = new HttpHeaders();
        plain.add("Authorization", "Basic abc");
        HttpHeaders readOnly = HttpHeaders.readOnlyHttpHeaders(plain);
        WebSocketHttpHeaders ws = new WebSocketHttpHeaders();
        ws.add("Authorization", "Basic abc");

        for (var e : new Object[][] {{"HttpHeaders", plain}, {"ReadOnlyHttpHeaders", readOnly}, {"WebSocketHttpHeaders", ws}}) {
            HttpHeaders h = (HttpHeaders) e[1];
            // asSingleValueMap() 이 돌려주는 어댑터의 toString 은 원래 맵(값 목록)을 찍으므로, get 과 size 로 본다
            var view = h.asSingleValueMap();
            System.out.printf("%-22s get=%s toSingleValueMap=%s asSingleValueMap().get=%s size=%d%n",
                    e[0], h.get("Authorization"), h.toSingleValueMap(), view.get("Authorization"), view.size());
        }
    }
}
