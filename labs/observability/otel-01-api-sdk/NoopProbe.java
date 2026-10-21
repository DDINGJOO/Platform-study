import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanContext;
import io.opentelemetry.api.trace.TraceFlags;
import io.opentelemetry.api.trace.TraceState;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Context;

/** A bounded API-only probe; no SDK, exporters, global registration, or timing claims. */
public final class NoopProbe {
  public static void main(String[] args) {
    Tracer tracer = OpenTelemetry.noop().getTracer("study.api-only");
    Span noParent = tracer.spanBuilder("no-parent").setNoParent().startSpan();
    System.out.println("no-parent isRecording=" + noParent.isRecording());
    System.out.println("no-parent contextValid=" + noParent.getSpanContext().isValid());
    check(!noParent.isRecording(), "No-parent span must not record");
    check(!noParent.getSpanContext().isValid(), "No-parent context must be invalid");
    noParent.end();
    System.out.println("no-parent PASS");

    SpanContext parent = SpanContext.createFromRemoteParent(
        "abcdefabcdefabcdefabcdefabcdefab", "abcdefabcdefabcd",
        TraceFlags.getSampled(), TraceState.getDefault());
    Span withParent = tracer.spanBuilder("with-parent")
        .setParent(Context.root().with(Span.wrap(parent))).startSpan();
    System.out.println("with-parent isRecording=" + withParent.isRecording());
    System.out.println("with-parent contextValid=" + withParent.getSpanContext().isValid());
    System.out.println("with-parent contextPreserved=" + parent.equals(withParent.getSpanContext()));
    check(!withParent.isRecording(), "Parented span must not record");
    check(withParent.getSpanContext().isValid(), "Explicit parent must remain valid");
    check(parent.equals(withParent.getSpanContext()), "Explicit parent context must be preserved");
    withParent.end();
    System.out.println("with-parent PASS");
  }

  private static void check(boolean condition, String message) {
    if (!condition) {
      throw new AssertionError(message);
    }
  }
}
