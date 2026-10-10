package lab.slo;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.stereotype.Component;

/** 실행 중에 바꾸는 장애 주입 상태. */
@Component
public class Chaos {

    volatile double errorRate = Double.parseDouble(System.getenv().getOrDefault("ERROR_RATE", "0"));
    volatile long latencyMs = 0;

    /** 초당 이만큼(MB) 버려지는 객체를 만든다. 0 이면 멈춘다. */
    volatile int allocMbPerSec = 0;
    /** 버리지 않고 붙잡아 두는 양(MB). 힙에 남는 데이터가 늘어나는 상황을 흉내 낸다. */
    volatile int retainMb = 0;

    private final List<byte[]> retained = new ArrayList<>();

    Chaos() {
        Thread t = new Thread(this::allocLoop, "alloc-storm");
        t.setDaemon(true);
        t.start();
    }

    private void allocLoop() {
        long sink = 0;
        while (true) {
            try {
                synchronized (retained) {
                    while (retained.size() < retainMb) retained.add(new byte[1024 * 1024]);
                    while (retained.size() > retainMb) retained.remove(retained.size() - 1);
                }
                int mb = allocMbPerSec;
                if (mb == 0) { Thread.sleep(200); continue; }
                // 1초를 10조각으로 나눠 할당한다. 조각마다 64KB 배열을 여러 개 만들고 바로 버린다
                long start = System.nanoTime();
                int chunks = mb * 16 / 10;
                for (int i = 0; i < chunks; i++) {
                    byte[] b = new byte[64 * 1024];
                    b[ThreadLocalRandom.current().nextInt(b.length)] = 1;
                    sink += b[0];
                }
                long spentMs = (System.nanoTime() - start) / 1_000_000;
                if (spentMs < 100) Thread.sleep(100 - spentMs);
            } catch (InterruptedException e) {
                return;
            } catch (OutOfMemoryError e) {
                // 붙잡은 양이 힙을 넘으면 여기로 온다. 프로세스는 살려 두고 기록만 남긴다
                System.err.println("alloc-storm: " + e);
            }
        }
    }

    int retainedMb() {
        synchronized (retained) { return retained.size(); }
    }
}
