package lab.co3;

/** konst 의 상수를 switch case 라벨에만 쓴다. */
public class SwitchUse {
    static String kind(String s) {
        switch (s) {
            case lab.konst.K.NAME: return "konst";
            default: return "other";
        }
    }
}
