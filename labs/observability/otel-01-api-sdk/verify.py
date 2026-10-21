#!/usr/bin/env python3
"""Compile and execute NoopProbe with API/context jars pinned by SHA-256."""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
VERSION = "1.67.0"
ARTIFACTS = {
    "opentelemetry-api": "538d1dff2f9a37aecbc0ef98fd17273a3affb058e734e6763a3a07a38a5fdc59",
    "opentelemetry-context": "40fb813fb5e27ec2691daa29c81b572b5b1541ef9b41e62490c3ee3e6407c55e",
    "opentelemetry-common": "da97bdb395418e16ecdcbe7ad3497f45b9e767ceda4ae7e86133e7a757ac377f",
}
EXPECTED_OUTPUT = """no-parent isRecording=false
no-parent contextValid=false
no-parent PASS
with-parent isRecording=false
with-parent contextValid=true
with-parent contextPreserved=true
with-parent PASS
"""


def main():
    with tempfile.TemporaryDirectory(prefix="otel-noop-probe-") as temporary:
        directory = Path(temporary)
        jars = []
        for artifact, expected in ARTIFACTS.items():
            name = f"{artifact}-{VERSION}.jar"
            url = f"https://repo.maven.apache.org/maven2/io/opentelemetry/{artifact}/{VERSION}/{name}"
            request = Request(url, headers={"User-Agent": "Platform-study-noop-probe"})
            with urlopen(request, timeout=30) as response:
                raw = response.read()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f"Artifact checksum mismatch: {artifact}")
            jar = directory / name
            jar.write_bytes(raw)
            jars.append(str(jar))
        classpath = os.pathsep.join(jars)
        subprocess.run(
            ["javac", "--release", "11", "-cp", classpath, "-d", str(directory), str(HERE / "NoopProbe.java")],
            check=True, capture_output=True, text=True,
        )
        result = subprocess.run(
            ["java", "-cp", os.pathsep.join([str(directory), classpath]), "NoopProbe"],
            check=False, capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError(f"Probe failed:\n{result.stdout}{result.stderr}")
        if result.stdout != EXPECTED_OUTPUT:
            raise AssertionError(f"Unexpected probe output: {result.stdout!r}")
        if result.stderr:
            raise AssertionError(f"Unexpected probe stderr: {result.stderr!r}")
        print(result.stdout, end="")
        print("API/context/common artifact SHA-256 checks: PASS")


if __name__ == "__main__":
    main()
