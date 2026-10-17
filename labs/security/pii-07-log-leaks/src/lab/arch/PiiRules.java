package lab.arch;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.base.DescribedPredicate;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaConstructorCall;
import com.tngtech.archunit.core.domain.JavaField;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.EvaluationResult;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import java.util.Set;
import java.util.stream.Collectors;
import lab.Pii;

/** 컴파일된 바이트코드를 읽어 세 규칙을 검사한다. JUnit 없이 main 으로 돌린다. */
public final class PiiRules {
    private PiiRules() {}

    /** 규칙 1: toString 이 @Pii 필드를 직접 읽거나 그 필드의 getter 를 부르면 위반. */
    static final ArchCondition<JavaClass> TO_STRING_SKIPS_PII = new ArchCondition<>("toString 에서 @Pii 필드를 읽지 않는다") {
        @Override
        public void check(JavaClass c, ConditionEvents events) {
            Set<String> pii = c.getAllFields().stream().filter(f -> f.isAnnotatedWith(Pii.class))
                    .map(JavaField::getName).collect(Collectors.toSet());
            if (pii.isEmpty()) return;
            for (JavaMethod m : c.getMethods()) {
                if (!m.getName().equals("toString") || !m.getRawParameterTypes().isEmpty()) continue;
                m.getFieldAccesses().stream().filter(a -> pii.contains(a.getTarget().getName())).forEach(a ->
                        events.add(SimpleConditionEvent.violated(c, c.getSimpleName() + ".toString 이 @Pii 필드 " + a.getTarget().getName() + " 를 읽음")));
                m.getMethodCallsFromSelf().stream().filter(call -> pii.stream().anyMatch(p ->
                        call.getTarget().getName().equalsIgnoreCase("get" + p))).forEach(call ->
                        events.add(SimpleConditionEvent.violated(c, c.getSimpleName() + ".toString 이 " + call.getTarget().getName() + "() 를 부름")));
            }
        }
    };

    /** 규칙 2: repo 패키지에서 Throwable 을 인자로 받는 예외 생성자를 부르면 위반(원인 예외를 달아 던지는 코드). */
    static final DescribedPredicate<JavaConstructorCall> WRAPS_CAUSE = new DescribedPredicate<>("원인 예외를 받는 예외 생성자") {
        @Override
        public boolean test(JavaConstructorCall call) {
            return call.getTargetOwner().isAssignableTo(Throwable.class)
                    && call.getTarget().getRawParameterTypes().stream().anyMatch(t -> t.isAssignableTo(Throwable.class));
        }
    };

    /**
     * 규칙 3: @Pii 구성 요소를 가진 record 는 toString 을 직접 선언해야 한다.
     * 컴파일러가 만든 record toString 은 invokedynamic(ObjectMethods.bootstrap) 하나라
     * ArchUnit 이 보는 필드 접근·메서드 호출이 하나도 없다. 그걸 "직접 선언하지 않았다"의 신호로 쓴다.
     */
    static final ArchCondition<JavaClass> RECORD_DECLARES_TO_STRING = new ArchCondition<>("@Pii record 는 toString 을 직접 선언한다") {
        @Override
        public void check(JavaClass c, ConditionEvents events) {
            if (!c.isRecord()) return;
            boolean pii = c.getAllFields().stream().anyMatch(f -> f.isAnnotatedWith(Pii.class));
            if (!pii) return;
            c.tryGetMethod("toString").ifPresent(m -> {
                if (m.getFieldAccesses().isEmpty() && m.getMethodCallsFromSelf().isEmpty()) {
                    events.add(SimpleConditionEvent.violated(c, c.getSimpleName() + " 는 컴파일러가 만든 toString 을 그대로 쓴다"));
                }
            });
        }
    };

    public static void main(String[] args) {
        JavaClasses all = new ClassFileImporter().importPackages("lab");
        ArchRule r1 = classes().should(TO_STRING_SKIPS_PII);
        ArchRule r2 = noClasses().that().resideInAPackage("..repo..").should().callConstructorWhere(WRAPS_CAUSE);
        int total = 0;
        ArchRule r3 = classes().should(RECORD_DECLARES_TO_STRING);
        for (ArchRule r : new ArchRule[] {r1, r2, r3}) {
            EvaluationResult res = r.evaluate(all);
            var lines = res.getFailureReport().getDetails();
            total += lines.size();
            System.out.println("규칙: " + r.getDescription());
            System.out.println("  위반 " + lines.size() + "건");
            lines.forEach(l -> System.out.println("    " + l.replaceAll(" in \\(.*\\)$", "")));
        }
        System.out.println("@Pii 를 가진 클래스: " + all.stream().filter(c -> c.getAllFields().stream()
                .anyMatch(f -> f.isAnnotatedWith(Pii.class))).map(JavaClass::getSimpleName).sorted().toList());
        System.out.println("위반 합계 " + total + "건");
    }
}
