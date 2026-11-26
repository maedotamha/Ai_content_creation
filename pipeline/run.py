"""One command for the whole pipeline:  python pipeline/run.py   (or: make film)

Order: validate -> narration -> keyframes -> shots -> music -> assemble.
Narration runs first because the voice sets each shot's length.
Every stage is cached, so a re-run only regenerates what changed in storyboard.json."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

from common import OUTPUTS, ROOT, RUNS_LOG, load_storyboard

HERE = ROOT / "pipeline"


def stage(name: str, *args: str) -> None:
    t0 = time.time()
    subprocess.run([sys.executable, str(HERE / f"{name}.py"), *args], check=True, cwd=ROOT)
    print(f"  ({name}: {time.time() - t0:.1f}s)\n")


def merge_kaggle_logs() -> None:
    """Append log lines from Kaggle runs (outputs/**/runs_kaggle.jsonl) once."""
    existing = set(RUNS_LOG.read_text(encoding="utf-8").splitlines()) if RUNS_LOG.exists() else set()
    new = []
    for f in OUTPUTS.rglob("runs_kaggle.jsonl"):
        new += [ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip() and ln not in existing]
    if new:
        with RUNS_LOG.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(new) + "\n")
        print(f"  merged {len(new)} Kaggle log lines into runs.jsonl\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio", action="store_true", help="narration + music only (radio cut)")
    args = ap.parse_args()

    n_before = sum(1 for _ in RUNS_LOG.open(encoding="utf-8")) if RUNS_LOG.exists() else 0
    sb = load_storyboard()
    print(f"storyboard OK: '{sb['title']}' - {len(sb['shots'])} shots\n")
    merge_kaggle_logs()

    stage("narration")
    if not args.radio:
        stage("keyframes")
        stage("shots")
    stage("music", "--duration", "120")
    stage("assemble", *(["--radio"] if args.radio else []))

    n_after = sum(1 for _ in RUNS_LOG.open(encoding="utf-8")) if RUNS_LOG.exists() else 0
    print(f"done. {n_after - n_before} new model calls logged to runs.jsonl")
    if n_after > n_before:
        for ln in RUNS_LOG.read_text(encoding="utf-8").splitlines()[n_before:]:
            r = json.loads(ln)
            print(f"  {r.get('stage')}/{r.get('shot')} {r.get('model')} {r.get('status')} {r.get('latency_s')}s")


if __name__ == "__main__":
    main()
