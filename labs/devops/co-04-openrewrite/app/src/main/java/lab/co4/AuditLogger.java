package lab.co4;

/** 사내 감사 로거. 메서드 이름만 info 로 같다. */
class AuditLogger {
    private int count;

    void info(String event) {
        count++;
    }

    int count() { return count; }
}
