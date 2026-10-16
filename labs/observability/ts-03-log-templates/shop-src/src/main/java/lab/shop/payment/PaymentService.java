package lab.shop.payment;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class PaymentService {
    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    public Payment authorize(Order order, Card card) {
        log.info("Payment {} authorized for order {} amount {} KRW", payment.id(), order.id(), order.total());
        return payment;
    }

    public void decline(Order order, String code) {
        log.warn("Payment declined for order {}: issuer code {}", order.id(), code);
    }

    public void refund(Payment p) {
        log.info("Refund {} issued for payment {} amount {} KRW", refund.id(), p.id(), p.amount());
    }

    public void onGatewaySlow(long ms) {
        log.warn("Payment gateway responded slowly: {} ms (threshold {} ms)", ms, thresholdMs);
    }
}
