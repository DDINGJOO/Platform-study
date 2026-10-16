// 묶음 219: RestTemplate 의 DefaultResponseErrorHandler 와 RestClient 의 StatusHandler 가 같은 오류 메시지 코드를 복사해 갖고 있다.
// 2024-04-30 커밋 4972d18dd6 가 앞쪽 메시지에만 HTTP 메서드와 URL 을 넣었다. 같은 500 응답에 두 클라이언트가 내는 메시지를 비교한다.
//   java -cp "$WORK/jars/6.2.0/*" demo/ErrorMessageDemo.java
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestTemplate;

public class ErrorMessageDemo {
    public static void main(String[] args) throws Exception {
        System.out.println("spring-web " + RestTemplate.class.getPackage().getImplementationVersion());
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/orders/42", ex -> { ex.sendResponseHeaders(500, -1); ex.close(); });
        server.start();
        String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/orders/42";
        try {
            try {
                new RestTemplate().getForObject(url, String.class);
            }
            catch (Exception ex) {
                System.out.println("RestTemplate: " + ex.getMessage().replace(url, "<url>"));
            }
            try {
                RestClient.create().get().uri(url).retrieve().body(String.class);
            }
            catch (Exception ex) {
                System.out.println("RestClient:   " + ex.getMessage().replace(url, "<url>"));
            }
        }
        finally {
            server.stop(0);
        }
    }
}
