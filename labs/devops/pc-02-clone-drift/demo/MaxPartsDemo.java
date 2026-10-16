// 묶음 210: PartEventHttpMessageReader 와 DefaultPartHttpMessageReader 의 "부분 수 세기" 코드.
// 2024-02-05 커밋 c570f3b2da 가 앞쪽에서만 off-by-one(gh-32122)을 고쳤다. 뒤쪽에도 같은 결함이 있는지 본다.
// 부분 2개짜리 multipart 본문을 maxParts=2 로 읽는다. 결함이 있으면 "Too many parts" 가 난다.
//   java -cp "$WORK/jars/<버전>/*" demo/MaxPartsDemo.java
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.springframework.core.ResolvableType;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ReactiveHttpInputMessage;
import org.springframework.http.codec.multipart.DefaultPartHttpMessageReader;
import org.springframework.http.codec.multipart.PartEventHttpMessageReader;
import reactor.core.publisher.Flux;

public class MaxPartsDemo {
    static final String BOUNDARY = "b0undary";

    static ReactiveHttpInputMessage message(int parts) {
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= parts; i++) {
            sb.append("--").append(BOUNDARY).append("\r\n")
              .append("Content-Disposition: form-data; name=\"f").append(i).append("\"\r\n\r\n")
              .append("v").append(i).append("\r\n");
        }
        sb.append("--").append(BOUNDARY).append("--\r\n");
        byte[] bytes = sb.toString().getBytes(StandardCharsets.UTF_8);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("multipart/form-data;boundary=" + BOUNDARY));
        return new ReactiveHttpInputMessage() {
            public HttpHeaders getHeaders() { return headers; }
            public Flux<DataBuffer> getBody() { return Flux.just(DefaultDataBufferFactory.sharedInstance.wrap(bytes)); }
        };
    }

    static String run(Flux<?> flux) {
        try {
            return "ok, " + flux.collectList().block().size() + " items";
        }
        catch (Exception ex) {
            return "error: " + ex.getMessage();
        }
    }

    public static void main(String[] args) {
        System.out.println("spring-web " + DefaultPartHttpMessageReader.class.getPackage().getImplementationVersion());
        for (int parts : new int[] {1, 2, 3}) {
            DefaultPartHttpMessageReader def = new DefaultPartHttpMessageReader();
            def.setMaxParts(2);
            PartEventHttpMessageReader ev = new PartEventHttpMessageReader();
            ev.setMaxParts(2);
            System.out.printf("parts=%d maxParts=2  DefaultPart: %-40s PartEvent: %s%n", parts,
                    run(def.read(ResolvableType.NONE, message(parts), Map.of())),
                    run(ev.read(ResolvableType.NONE, message(parts), Map.of())));
        }
    }
}
