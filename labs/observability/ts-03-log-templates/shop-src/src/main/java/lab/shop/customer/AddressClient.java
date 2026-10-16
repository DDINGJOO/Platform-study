package lab.shop.customer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AddressClient {
    private static final Logger log = LoggerFactory.getLogger(AddressClient.class);

    public Address fetch(String customerId) {
        try {
            return http.get(baseUrl + "/addresses/" + customerId);
        } catch (TimeoutException e) {
            log.error("Address lookup for customer {} timed out after {} ms (endpoint {})", customerId, timeoutMs, baseUrl);
            return null;
        } catch (HttpException e) {
            log.error("Address lookup for customer {} failed with HTTP {} (endpoint {})", customerId, e.status(), baseUrl);
            return null;
        }
    }

    public void onRetry(String customerId, int attempt) {
        log.warn("Retrying address lookup for customer {} (attempt {} of {})", customerId, attempt, maxAttempts);
    }
}
