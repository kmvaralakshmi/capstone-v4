
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def run(cmd):
    print("\n>>>", " ".join(map(str,cmd)))
    return subprocess.run(cmd,cwd=ROOT).returncode

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--skip-download",action="store_true")
    args=p.parse_args()
    if not args.skip_download:
        rc=run([sys.executable,str(ROOT/"helper-scripts"/"download_brsr_reports.py")])
        if rc != 0: return rc
    return run([sys.executable,str(ROOT/"demo.py")])

if __name__=="__main__":
    raise SystemExit(main())
