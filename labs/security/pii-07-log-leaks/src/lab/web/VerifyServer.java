package lab.web;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/** ④ 외부 본인확인 API 를 흉내 내는 로컬 서버. 받은 전화번호를 응답에 되돌려 준다. */
public final class VerifyServer {
    private VerifyServer() {}

    public static HttpServer start(int port) throws IOException {
        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        s.createContext("/verify", ex -> {
            String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            String phone = body.replaceAll("(?s).*\"phone\":\"([^\"]*)\".*", "$1");
            byte[] out = ("{\"result\":\"MATCH\",\"phone\":\"" + phone + "\"}").getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().add("Content-Type", "application/json");
            ex.sendResponseHeaders(200, out.length);
            ex.getResponseBody().write(out);
            ex.close();
        });
        s.start();
        return s;
    }
}
