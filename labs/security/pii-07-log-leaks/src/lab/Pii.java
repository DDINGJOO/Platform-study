package lab;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** 개인정보 필드 표시. RUNTIME 이라 TurboFilter(리플렉션)와 ArchUnit(바이트코드)이 둘 다 본다. */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.RECORD_COMPONENT})
public @interface Pii {}
