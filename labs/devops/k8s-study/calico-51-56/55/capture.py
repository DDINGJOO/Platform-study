#!/usr/bin/env python3
"""Use an experiment-local reviewed allowlist without changing shared policy."""
from pathlib import Path
import importlib.util
import sys
base=Path(__file__).resolve().parent
path=Path('/Users/dding/orca/Platform-study/.claude/skills/blog-post-pipeline/assets/term-shot.py')
spec=importlib.util.spec_from_file_location('termshot55',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
mod.ROOT=str(base)
sys.argv[0]=str(path)
mod.main()
