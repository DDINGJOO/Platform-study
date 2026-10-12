package lab.co3;

import java.util.function.Supplier;

/** m4: 어느 c 가 클래스패스에 올라왔는지 보고, 각 라이브러리를 실제로 불러 본다. */
public class Main {
    public static void main(String[] args) throws Exception {
        // c 를 직접 import 하지 않으려고 리플렉션으로 버전을 읽는다
        Object v = Class.forName("lab.c.Codec").getMethod("version").invoke(null);
        System.out.println("RESULT m4 c=" + v);
        call("y", () -> lab.y.Y.run());
        call("x", () -> lab.x.X.run());
    }

    static void call(String name, Supplier<String> s) {
        try {
            System.out.println("RESULT m4 " + name + " OK " + s.get());
        } catch (Throwable t) {
            System.out.println("RESULT m4 " + name + " FAIL " + t.getClass().getSimpleName() + ": " + t.getMessage());
        }
    }
}
