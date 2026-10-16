package lab.shop.customer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class CustomerService {
    private static final Logger log = LoggerFactory.getLogger(CustomerService.class);

    public Customer load(String customerId) {
        log.debug("Loading customer {} from cache", customerId);
        Customer c = cache.get(customerId);
        if (c == null) {
            log.info("Cache miss for customer {}, loading from database", customerId);
            c = repository.find(customerId);
        }
        return c;
    }

    public void validate(Customer c) {
        if (c.address() == null) {
            log.error("Error processing customer {}: Address Missing.", c.id());
            throw new ValidationException("address");
        }
        if (!c.address().hasPostalCode()) {
            log.warn("Error processing customer {}: Postal Code Missing, using region default {}", c.id(), c.region());
        }
    }

    public void updateAddress(Customer c, Address a) {
        log.info("Customer {} address updated to region {}", c.id(), a.region());
    }
}
