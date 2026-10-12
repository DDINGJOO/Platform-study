package lab.co4;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;
import java.util.function.Function;

/** 표준 라이브러리 HTTP 서버. 경로마다 핸들러 하나. */
public class App {
    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
        server.setExecutor(Executors.newFixedThreadPool(8));
        OrderHandler orders = new OrderHandler();
        PaymentHandler payments = new PaymentHandler();
        SearchHandler search = new SearchHandler();
        LegacyAdminHandler admin = new LegacyAdminHandler();
        route(server, "/orders", q -> orders.handle(param(q, "id")));
        route(server, "/payments", q -> payments.handle(param(q, "id")));
        route(server, "/search", q -> search.handle(param(q, "q")));
        route(server, "/items", q -> search.items(param(q, "q")));
        route(server, "/admin/legacy", q -> admin.handle());   // 부하 스크립트는 이 경로를 부르지 않는다
        route(server, "/health", q -> "ok");
        server.start();
        System.out.println("listening on 8080");
    }

    static void route(HttpServer s, String path, Function<URI, String> f) {
        s.createContext(path, ex -> respond(ex, f.apply(ex.getRequestURI())));
    }

    static String param(URI uri, String key) {
        String q = uri.getRawQuery();
        if (q == null) return "";
        for (String kv : q.split("&")) {
            String[] p = kv.split("=", 2);
            if (p[0].equals(key) && p.length == 2) return p[1];
        }
        return "";
    }

    static void respond(HttpExchange ex, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.sendResponseHeaders(200, b.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(b); }
    }
}
