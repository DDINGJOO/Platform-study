package lab.compat;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class CompatApplication {
    public static void main(String[] args) {
        SpringApplication.run(CompatApplication.class, args);
    }

    @GetMapping("/hello")
    @CircuitBreaker(name = "hello")
    public String hello() {
        return "hello";
    }
}
