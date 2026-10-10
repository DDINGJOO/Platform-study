package lab.shop;

import java.util.List;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/** 메시지를 한 건씩 받는 리스너(기본). */
@Profile("payment")
@Component
@ConditionalOnProperty(name = "shop.payment.batch", havingValue = "false", matchIfMissing = true)
class PaymentListener {

    private final PaymentWorker worker;

    PaymentListener(PaymentWorker worker) {
        this.worker = worker;
    }

    @KafkaListener(topics = "orders")
    void onOrder(ConsumerRecord<String, String> record) {
        worker.accept(record.value());
    }
}

/** poll 한 번에 온 메시지를 묶음으로 받는 리스너. */
@Profile("payment")
@Component
@ConditionalOnProperty(name = "shop.payment.batch", havingValue = "true")
class PaymentBatchListener {

    private final PaymentWorker worker;

    PaymentBatchListener(PaymentWorker worker) {
        this.worker = worker;
    }

    @KafkaListener(topics = "orders", batch = "true")
    void onOrders(List<ConsumerRecord<String, String>> records) {
        records.forEach(r -> worker.accept(r.value()));
    }
}
