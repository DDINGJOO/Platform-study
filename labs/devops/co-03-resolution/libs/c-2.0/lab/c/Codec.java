package lab.c;

public class Codec {
    public static String version() { return "2.0"; }
    public static String encode(String s) { return "c2:" + s; }
    /** 2.0 에서 새로 생겼다. */
    public static String encodeFast(String s) { return "fast:" + s; }
}
