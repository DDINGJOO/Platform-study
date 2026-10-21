import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanContext;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.TraceFlags;
import io.opentelemetry.api.trace.TraceState;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.ContextKey;
import io.opentelemetry.context.Scope;
import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.ReadWriteSpan;
import io.opentelemetry.sdk.trace.ReadableSpan;
import io.opentelemetry.sdk.trace.SpanProcessor;
import io.opentelemetry.sdk.trace.data.LinkData;
import io.opentelemetry.sdk.trace.data.SpanData;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.sdk.trace.export.SimpleSpanProcessor;
import io.opentelemetry.sdk.trace.export.SpanExporter;
import io.opentelemetry.sdk.trace.samplers.Sampler;
import io.opentelemetry.sdk.trace.samplers.SamplingResult;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Controlled behavior probes, not a benchmark or a modified OpenTelemetry build. */
public final class RuntimeProbes {
  public static void main(String[] args) throws Exception {
    switch (args[0]) {
      case "context": context(); break;
      case "batch": batch(); break;
      case "sampling": sampling(); break;
      case "api-sdk": apiSdk(); break;
      default: throw new IllegalArgumentException("Unknown probe: " + args[0]);
    }
  }

  @SuppressWarnings("try") // Scope exists for deterministic close, not for reading its value.
  private static void context() throws Exception {
    ContextKey<String> key = ContextKey.named("study-owner");
    Context callerBefore = Context.current();
    Context workerBaseline = Context.root().with(key, "worker-baseline");
    AtomicReference<Thread> wrappedThread = new AtomicReference<>();
    ExecutorService worker = Executors.newSingleThreadExecutor(task -> new Thread(() -> {
      try (Scope ignored = workerBaseline.makeCurrent()) {
        task.run();
      }
    }, "context-probe-worker"));
    try {
      String unwrapped = worker.submit(() -> Context.current().get(key)).get(10, TimeUnit.SECONDS);
      check("worker-baseline".equals(unwrapped), "Worker baseline missing");
      System.out.println("context unwrapped=" + unwrapped);
      Runnable wrapped;
      try (Scope ignored = Context.root().with(key, "captured").makeCurrent()) {
        wrapped = Context.current().wrap((Runnable) () -> {
          wrappedThread.set(Thread.currentThread());
          String observed = Context.current().get(key);
          check("captured".equals(observed), "Captured context not attached");
          System.out.println("context wrapped=" + observed);
          throw new ExpectedFailure();
        });
      }
      try {
        worker.submit(wrapped).get(10, TimeUnit.SECONDS);
        throw new AssertionError("Wrapped task did not throw");
      } catch (ExecutionException exception) {
        check(exception.getCause() instanceof ExpectedFailure, "Unexpected task failure");
        System.out.println("context exception=ExpectedFailure");
      }
      String restored = worker.submit(() -> {
        check(Thread.currentThread() == wrappedThread.get(), "A different worker was used");
        return Context.current().get(key);
      }).get(10, TimeUnit.SECONDS);
      check("worker-baseline".equals(restored), "Worker context was not restored");
      check(Context.current() == callerBefore, "Caller context was not restored");
      System.out.println("context worker-restored=" + restored);
      System.out.println("context same-worker=true");
      System.out.println("context caller-restored=true");
      System.out.println("context PASS");
    } finally {
      worker.shutdownNow();
      check(worker.awaitTermination(10, TimeUnit.SECONDS), "Worker did not stop");
    }
  }

  private static void batch() throws Exception {
    GateExporter exporter = new GateExporter();
    BatchSpanProcessor processor = BatchSpanProcessor.builder(exporter)
        .setMaxQueueSize(2).setMaxExportBatchSize(1)
        .setScheduleDelay(Duration.ofDays(1)).setExporterTimeout(Duration.ofDays(1)).build();
    SdkTracerProvider provider = SdkTracerProvider.builder().addSpanProcessor(processor).build();
    try {
      Tracer tracer = provider.get("study.batch");
      endRecorded(tracer, "in-flight");
      CompletableResultCode initialFlush = processor.forceFlush();
      check(exporter.entered.await(10, TimeUnit.SECONDS), "First export was not entered");
      check(!exporter.pending.isDone(), "First export completed too early");
      for (String name : new String[] {"queued-a", "queued-b", "overflow-c", "overflow-d", "overflow-e"}) {
        endRecorded(tracer, name);
      }
      check(exporter.names.isEmpty(), "Export completed while gate was closed");
      System.out.println("batch queue-capacity=2 batch-size=1 first-export-pending=true");
      System.out.println("batch spans-ended-while-export-pending=5");
      exporter.release();
      completed(initialFlush, "initial forceFlush");
      completed(processor.forceFlush(), "final forceFlush");
      check(exporter.names.size() == 3, "Unexpected exported count: " + exporter.names);
      check(exporter.names.contains("in-flight") && exporter.names.contains("queued-a")
          && exporter.names.contains("queued-b"), "Unexpected exported span names");
      check(!exporter.names.contains("overflow-c") && !exporter.names.contains("overflow-d")
          && !exporter.names.contains("overflow-e"), "Overflow spans were exported");
      System.out.println("batch recording-spans-ended=6 exported=3 not-exported=3");
      System.out.println("batch exported-names=in-flight,queued-a,queued-b");
      System.out.println("batch PASS");
    } finally {
      exporter.release();
      completed(provider.shutdown(), "batch provider shutdown");
    }
  }

  private static void sampling() {
    try (SdkTracerProvider defaults = SdkTracerProvider.builder()
             .addSpanProcessor(new EndCountingProcessor()).build();
         SdkTracerProvider alwaysOn = SdkTracerProvider.builder().setSampler(Sampler.alwaysOn())
             .addSpanProcessor(new EndCountingProcessor()).build();
         SdkTracerProvider alwaysOff = SdkTracerProvider.builder().setSampler(Sampler.alwaysOff())
             .addSpanProcessor(new EndCountingProcessor()).build()) {
      sample(defaults, "default-root", Context.root(), true, true);
      sample(defaults, "default-remote-sampled-parent", parent(true), true, true);
      sample(defaults, "default-remote-unsampled-parent", parent(false), false, false);
      sample(alwaysOn, "always-on-remote-unsampled-parent", parent(false), true, true);
      sample(alwaysOff, "always-off-remote-sampled-parent", parent(true), false, false);
    }
    Sampler recordOnly = new Sampler() {
      @Override public SamplingResult shouldSample(Context parent, String traceId, String name,
          SpanKind kind, Attributes attributes, List<LinkData> links) {
        return SamplingResult.recordOnly();
      }
      @Override public String getDescription() { return "StudyRecordOnly"; }
    };
    recordOnly(recordOnly, false, 0);
    recordOnly(recordOnly, true, 1);
    System.out.println("sampling PASS");
  }

  private static void recordOnly(Sampler sampler, boolean includeUnsampled, int expectedExports) {
    CountingExporter exporter = new CountingExporter();
    SimpleSpanProcessor processor = SimpleSpanProcessor.builder(exporter)
        .setExportUnsampledSpans(includeUnsampled).build();
    try (SdkTracerProvider provider = SdkTracerProvider.builder().setSampler(sampler)
        .addSpanProcessor(processor).build()) {
      Span span = provider.get("study.sampling").spanBuilder("record-only").setNoParent().startSpan();
      check(span.isRecording(), "RECORD_ONLY span must record");
      check(!span.getSpanContext().isSampled(), "RECORD_ONLY must clear sampled flag");
      span.end();
      completed(provider.forceFlush(), "record-only forceFlush");
      check(exporter.names.size() == expectedExports, "Unexpected RECORD_ONLY export count");
      System.out.println("sampling record-only include-unsampled=" + includeUnsampled
          + " recording=true sampled=false exported=" + exporter.names.size());
    }
  }

  private static void sample(SdkTracerProvider provider, String label, Context parent,
      boolean recording, boolean sampled) {
    Span span = provider.get("study.sampling").spanBuilder(label).setParent(parent).startSpan();
    check(span.isRecording() == recording, "Unexpected recording state: " + label);
    check(span.getSpanContext().isSampled() == sampled, "Unexpected sampled flag: " + label);
    check(span.getSpanContext().isValid(), "SDK span context should be valid: " + label);
    System.out.println("sampling " + label + " recording=" + span.isRecording()
        + " sampled=" + span.getSpanContext().isSampled());
    span.end();
  }

  private static Context parent(boolean sampled) {
    SpanContext context = SpanContext.createFromRemoteParent(
        "abcdefabcdefabcdefabcdefabcdefab", "abcdefabcdefabcd",
        sampled ? TraceFlags.getSampled() : TraceFlags.getDefault(), TraceState.getDefault());
    return Context.root().with(Span.wrap(context));
  }

  private static void apiSdk() {
    Span noop = OpenTelemetry.noop().getTracer("study.boundary")
        .spanBuilder("noop").setNoParent().startSpan();
    check(!noop.isRecording() && !noop.getSpanContext().isValid(), "Unexpected noop root");
    System.out.println("api-sdk noop-root recording=false context-valid=false");
    noop.end();
    try (SdkTracerProvider provider = SdkTracerProvider.builder().build()) {
      Span recording = provider.get("study.boundary").spanBuilder("no-processor").setNoParent().startSpan();
      check(!recording.isRecording() && !recording.getSpanContext().isValid(),
          "Expected SDK no-processor noop optimization");
      System.out.println("api-sdk sdk-no-processor recording=false context-valid=false configured-exporters=0");
      recording.end();
    }
    EndCountingProcessor observer = new EndCountingProcessor();
    try (SdkTracerProvider provider = SdkTracerProvider.builder().addSpanProcessor(observer).build()) {
      Span recording = provider.get("study.boundary").spanBuilder("observe-only").setNoParent().startSpan();
      check(recording.isRecording() && recording.getSpanContext().isValid(), "SDK did not record");
      recording.end();
      check(observer.ended.get() == 1, "Observer did not see ended recording span");
      System.out.println("api-sdk sdk-observer-only recording=true context-valid=true ended-observed=1 configured-exporters=0");
    }
    CountingExporter exporter = new CountingExporter();
    try (SdkTracerProvider provider = SdkTracerProvider.builder()
        .addSpanProcessor(SimpleSpanProcessor.create(exporter)).build()) {
      Span recording = provider.get("study.boundary").spanBuilder("with-exporter").setNoParent().startSpan();
      check(recording.isRecording() && recording.getSpanContext().isValid(), "Exporting SDK did not record");
      check(exporter.names.isEmpty(), "Span exported before end");
      recording.end();
      completed(provider.forceFlush(), "boundary forceFlush");
      check(exporter.names.equals(Collections.singletonList("with-exporter")), "Unexpected exported spans");
      System.out.println("api-sdk sdk-with-processor recording=true context-valid=true exported-after-end=1");
    }
    System.out.println("api-sdk PASS");
  }

  private static void endRecorded(Tracer tracer, String name) {
    Span span = tracer.spanBuilder(name).setNoParent().startSpan();
    check(span.isRecording(), "Batch span did not record: " + name);
    span.end();
  }

  private static void completed(CompletableResultCode result, String operation) {
    result.join(10, TimeUnit.SECONDS);
    check(result.isSuccess(), operation + " failed or timed out");
  }

  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }

  private static final class ExpectedFailure extends RuntimeException {
    private static final long serialVersionUID = 1L;
  }

  private static final class EndCountingProcessor implements SpanProcessor {
    final AtomicInteger ended = new AtomicInteger();
    @Override public void onStart(Context parent, ReadWriteSpan span) {}
    @Override public boolean isStartRequired() { return false; }
    @Override public void onEnd(ReadableSpan span) { ended.incrementAndGet(); }
    @Override public boolean isEndRequired() { return true; }
  }

  private static class CountingExporter implements SpanExporter {
    final List<String> names = Collections.synchronizedList(new ArrayList<>());
    @Override public CompletableResultCode export(Collection<SpanData> spans) {
      for (SpanData span : spans) names.add(span.getName());
      return CompletableResultCode.ofSuccess();
    }
    @Override public CompletableResultCode flush() { return CompletableResultCode.ofSuccess(); }
    @Override public CompletableResultCode shutdown() { return CompletableResultCode.ofSuccess(); }
  }

  private static final class GateExporter extends CountingExporter {
    final CountDownLatch entered = new CountDownLatch(1);
    final CompletableResultCode pending = new CompletableResultCode();
    final AtomicBoolean first = new AtomicBoolean(true);
    final AtomicBoolean released = new AtomicBoolean(false);
    volatile List<String> firstNames = Collections.emptyList();
    @Override public CompletableResultCode export(Collection<SpanData> spans) {
      if (first.compareAndSet(true, false)) {
        List<String> captured = new ArrayList<>();
        for (SpanData span : spans) captured.add(span.getName());
        firstNames = captured;
        entered.countDown();
        return pending;
      }
      return super.export(spans);
    }
    void release() {
      if (released.compareAndSet(false, true)) {
        names.addAll(firstNames);
        pending.succeed();
      }
    }
  }
}
