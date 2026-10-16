package lab.shop.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    public Order create(Cart cart, User user) {
        log.info("Order {} created for user {} with {} items", cart.orderId(), user.name(), cart.size());
        Order order = repository.save(cart.toOrder());
        log.debug("Order {} persisted in {} ms", order.id(), timer.elapsed());
        return order;
    }

    public void confirm(Order order) {
        log.info("Order {} confirmed, total {} KRW", order.id(), order.total());
    }

    public void cancel(Order order, String reason) {
        log.warn("Order {} cancelled by user {}: {}", order.id(), order.userName(), reason);
    }

    public void ship(Order order) {
        log.info("Shipping label requested for order {} to region {}", order.id(), order.region());
    }

    public void process(Order order) {
        try {
            invoice.issue(order);
        } catch (InvoiceException e) {
            log.error("Error processing order {}: invoice service returned {}", order.id(), e.status());
        }
    }
}
