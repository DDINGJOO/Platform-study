package lab.shop.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class OrderController {
    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    public Response handle(Request req) {
        log.info("{} {} from {} completed with status {} in {} ms", req.method(), req.path(), req.clientIp(), res.status(), timer.elapsed());
        return res;
    }

    public Response reject(Request req) {
        log.warn("Rejected request {} {} from {}: rate limit {} per second exceeded", req.method(), req.path(), req.clientIp(), limiter.rate());
        return Response.tooMany();
    }
}
