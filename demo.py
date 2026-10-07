"""Run all ESG agents sequentially and copy outputs to demo-output."""

from pathlib import Path
from shutil import copy2
import subprocess
import sys

from utils.config import PROCESSED_DATA_DIR, OUTPUT_FILES


BASE_DIR = Path(__file__).resolve().parent
DEMO_OUTPUT_DIR = BASE_DIR / "demo-output"


def run_agents() -> None:
    """Run Agent 1 to Agent 7 in order."""
    pipeline = [
        ("Agent 1", BASE_DIR / "agents" / "agent1_brsr_extractor.py"),
        ("Agent 2", BASE_DIR / "agents" / "agent2_environmental_risk.py"),
        ("Agent 3", BASE_DIR / "agents" / "agent3_news_sentiment.py"),
        ("Agent 4", BASE_DIR / "agents" / "agent4_stock_correlation.py"),
        ("Agent 5", BASE_DIR / "agents" / "agent5_greenwashing_detector.py"),
        ("Agent 6", BASE_DIR / "agents" / "agent6_master_scorer.py"),
        ("Agent 7", BASE_DIR / "agents" / "agent7_explainable_ai.py"),
    ]

    for name, script_path in pipeline:
        print(f"\nRunning {name}...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def collect_outputs() -> None:
    """Copy generated files from processed-data into demo-output."""
    DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_keys = [
        "brsr_metrics",
        "environmental_risk",
        "news_sentiment",
        "news_rejected",
        "stock_correlation",
        "greenwashing",
        "master_scores",
        "cross_validation",
        "data_quality",
        "external_benchmark",
        "run_metadata",
        "explanations",
    ]

    copied = 0
    for key in output_keys:
        file_name = OUTPUT_FILES[key]
        source_path = PROCESSED_DATA_DIR / file_name
        target_path = DEMO_OUTPUT_DIR / file_name

        if source_path.exists():
            copy2(source_path, target_path)
            copied += 1
            print(f"Copied: {target_path}")
        else:
            print(f"Missing output: {source_path}")

    print(f"\nDemo output folder: {DEMO_OUTPUT_DIR}")
    print(f"Files copied: {copied}")


def main() -> None:
    run_agents()
    collect_outputs()


if __name__ == "__main__":
    main()
