package lab;

public final class Masking {
    private Masking() {}

    /** 앞 6자리만 남긴다. 길이가 다르면 길이만 말한다. */
    public static String rrn(String v) {
        if (v == null) return "null";
        return v.length() >= 6 ? v.substring(0, 6) + "-*******" : "(len=" + v.length() + ")";
    }

    /** 끝 4자리만 남긴다. */
    public static String phone(String v) {
        if (v == null) return "null";
        return v.length() >= 4 ? "***-****-" + v.substring(v.length() - 4) : "(len=" + v.length() + ")";
    }

    public static String name(String v) {
        if (v == null || v.isEmpty()) return "null";
        return v.charAt(0) + "*".repeat(v.length() - 1);
    }
}
