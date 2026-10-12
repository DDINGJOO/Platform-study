package lab.c;

public class Codec {
    public static String version() { return "1.0"; }
    public static String encode(String s) { return "c1:" + s; }
    /** 1.0 에만 있다. 2.0 에서 지워졌다. */
    public static String legacy(String s) { return "legacy:" + s; }
}
