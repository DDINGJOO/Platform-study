package lab.co3.plain;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class PlainApp {
    public static void main(String[] args) { SpringApplication.run(PlainApp.class, args); }

    @GetMapping("/hello")
    public String hello() { return "hello"; }
}
