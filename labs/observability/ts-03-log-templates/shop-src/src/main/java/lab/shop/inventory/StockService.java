package lab.shop.inventory;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class StockService {
    private static final Logger log = LoggerFactory.getLogger(StockService.class);

    public void reserve(String sku, int qty) {
        log.info("Reserved {} units of {} in warehouse {}", qty, sku, warehouse.code());
    }

    public void lowStock(String sku, int left) {
        log.warn("Low stock for {}: {} units left in warehouse {}", sku, left, warehouse.code());
    }

    public void loadStateIndex(int index, String state) {
        log.info("Loaded State Index {} - {} into memory ({} entries)", index, state, entries);
    }

    public void failStateIndex(int index, String state, Exception e) {
        log.error("Error loading State Index {} - {} into memory", index, state, e);
    }
}
