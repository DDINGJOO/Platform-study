package lab.pp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class PpApplication {
    public static void main(String[] args) {
        SpringApplication.run(PpApplication.class, args);
    }
}
