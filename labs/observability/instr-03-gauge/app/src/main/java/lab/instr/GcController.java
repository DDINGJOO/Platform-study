package lab.instr;

import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.util.stream.Collectors;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GcController {

    // System.gc() 를 부른다. 명세상 "부탁"이라 실행 보장은 없다
    @PostMapping("/gc")
    String gc() {
        System.gc();
        return collectors();
    }

    // System.gc() 없이 쓰레기만 만든다. 평소 GC 로도 같은 일이 생기는지 본다
    @PostMapping("/alloc")
    String alloc(@RequestParam(defaultValue = "200") int mb) {
        long sink = 0;
        for (int i = 0; i < mb; i++) {
            byte[] chunk = new byte[1024 * 1024];
            sink += chunk.length;
        }
        return "allocated " + (sink >> 20) + "MB\n" + collectors();
    }

    private static String collectors() {
        return ManagementFactory.getGarbageCollectorMXBeans().stream()
                .map(GarbageCollectorMXBean::getName)
                .map(n -> n + "=" + ManagementFactory.getGarbageCollectorMXBeans().stream()
                        .filter(b -> b.getName().equals(n)).findFirst().get().getCollectionCount())
                .collect(Collectors.joining(", ")) + "\n";
    }
}
