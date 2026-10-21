#!/usr/bin/env python3
"""Compile and run controlled OpenTelemetry Java 1.67.0 behavior probes."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
VERSION = "1.67.0"
UPSTREAM_COMMIT = "b4b3a1b354425c3f1411173c0e48cb24a1cba224"
ARTIFACTS = {
    "opentelemetry-api": "538d1dff2f9a37aecbc0ef98fd17273a3affb058e734e6763a3a07a38a5fdc59",
    "opentelemetry-context": "40fb813fb5e27ec2691daa29c81b572b5b1541ef9b41e62490c3ee3e6407c55e",
    "opentelemetry-common": "da97bdb395418e16ecdcbe7ad3497f45b9e767ceda4ae7e86133e7a757ac377f",
    "opentelemetry-sdk-common": "628a4c00db9561ff4c608a650d5e7fd66a1e153ccdf1ba3cdc5ac0b7c6518fea",
    "opentelemetry-sdk-trace": "14d9615c8a5dcf471dcbb74902b771dcfa8656b755ac38dce904042289ccd198",
}


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=40)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command[0]}\n{result.stdout}{result.stderr}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each deterministic probe")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    with tempfile.TemporaryDirectory(prefix="otel-runtime-probes-") as temporary:
        directory = Path(temporary)
        jars, artifacts = [], []
        for artifact, expected in ARTIFACTS.items():
            name = f"{artifact}-{VERSION}.jar"
            url = f"https://repo.maven.apache.org/maven2/io/opentelemetry/{artifact}/{VERSION}/{name}"
            request = Request(url, headers={"User-Agent": "Platform-study-runtime-probes"})
            with urlopen(request, timeout=30) as response:
                raw = response.read()
            actual = hashlib.sha256(raw).hexdigest()
            if actual != expected:
                raise ValueError(f"Artifact checksum mismatch: {artifact}")
            jar = directory / name
            jar.write_bytes(raw)
            jars.append(str(jar))
            artifacts.append({"coordinate": f"io.opentelemetry:{artifact}:{VERSION}",
                              "url": url, "sha256": actual})
        classpath = os.pathsep.join(jars)
        source = HERE / "RuntimeProbes.java"
        compilation = run(["javac", "--release", "11", "-Xlint:all", "-cp", classpath,
                           "-d", str(directory), str(source)])
        if compilation.stderr:
            raise AssertionError(f"Compiler diagnostics:\n{compilation.stderr}")
        probes = {}
        for probe in ["api-sdk", "context", "batch", "sampling"]:
            observed = None
            expected_stderr = (
                "BatchSpanProcessor dropped 3 span(s) since the last export because the queue is full (maxQueueSize=2)\n"
                if probe == "batch" else ""
            )
            for _ in range(args.repeat):
                result = run(["java", "-Djava.util.logging.SimpleFormatter.format=%5$s%n",
                              "-cp", os.pathsep.join([str(directory), classpath]),
                              "RuntimeProbes", probe])
                if result.stderr != expected_stderr:
                    raise AssertionError(f"Unexpected stderr for {probe}: {result.stderr}")
                if observed is not None and observed != result.stdout:
                    raise AssertionError(f"Probe {probe} output changed across runs")
                observed = result.stdout
            if not observed.endswith(f"{probe} PASS\n"):
                raise AssertionError(f"Missing PASS marker: {probe}")
            probes[probe] = {"runs": args.repeat, "exit_code": 0,
                             "stdout": observed.splitlines(), "stderr": expected_stderr.splitlines()}
            print(observed, end="")
        evidence = {
            "kind": "observed-local-execution",
            "upstream_version": VERSION,
            "source_reference_commit": UPSTREAM_COMMIT,
            "java_version": run(["java", "-version"]).stderr.splitlines(),
            "javac_target": "--release 11",
            "javac_diagnostics": compilation.stderr.splitlines(),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "artifact_checksums_verified": True,
            "repeat_output_identical": True,
            "artifacts": artifacts,
            "probes": probes,
            "limits": [
                "Controlled in-memory exporter, not OTLP or backend durability",
                "No full upstream source build or patched OpenTelemetry source",
                "No timing, throughput, or zero-overhead measurement",
                "Timeouts only prevent hangs; latches and completion gates establish ordering",
                "Batch overflow counts apply to the explicit queue=2, batch=1 configuration",
                "Default sampler results apply to programmatic SdkTracerProvider with no autoconfiguration",
            ],
        }
        print("\nVALIDATION_JSON")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
