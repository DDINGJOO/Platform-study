package lab.co3;

import lab.b.B;
import lab.c.Codec;   // 직접 선언했다

/** an-decl: c 를 직접 쓴다. */
public class Main {
    public static void main(String[] args) throws Exception {
        System.out.println("RESULT an-decl c=" + Codec.version() + " " + Codec.encode("an-decl"));
        System.out.println("RESULT an-decl b " + B.run());
    }
}
