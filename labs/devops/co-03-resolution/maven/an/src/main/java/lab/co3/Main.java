package lab.co3;

import lab.b.B;
import lab.c.Codec;   // 선언하지 않았다. b -> d -> c 로 들어온다

/** an: c 를 직접 쓴다. */
public class Main {
    public static void main(String[] args) throws Exception {
        System.out.println("RESULT an c=" + Codec.version() + " " + Codec.encode("an"));
        System.out.println("RESULT an b " + B.run());
        // e 는 선언만 하고 쓰지 않는다
        // drv 는 리플렉션으로만 읽는다
        Object drv = Class.forName("lab.drv.Driver").getDeclaredConstructor().newInstance();
        System.out.println("RESULT an drv " + drv);
        // konst 는 컴파일 타임 상수만 쓴다
        System.out.println("RESULT an konst " + lab.konst.K.NAME);
    }
}
