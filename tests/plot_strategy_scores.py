"""
Plot model-level average scores based on tests/strategy_scores.csv.

Generates three bar charts:
- model_avg_overall.png       : Overall average score per model
- model_avg_robustness.png    : Robustness average score per model
- model_avg_quality_components.png : Code quality sub-dimensions per model

Usage:
    python tests/plot_strategy_scores.py
"""

from pathlib import Path
from typing import Dict, List
import csv

import matplotlib.pyplot as plt


ROOT_DIR = Path(__file__).resolve().parent
CSV_PATH = ROOT_DIR / "strategy_scores.csv"


def load_scores(path: Path) -> List[Dict[str, str]]:
    """Load per-strategy scores from CSV."""
    if not path.exists():
        print(f"CSV file not found: {path}")
        return []

    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def aggregate_by_model(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    """
    Aggregate scores by model.

    Returns:
        { model: { 'count': n, 'overall': avg, 'robustness': avg, ... }, ... }
    """
    agg: Dict[str, Dict[str, float]] = {}

    keys = [
        "overall",
        "robustness",
        "quality_overall",
        "structure",
        "error_handling",
        "documentation",
        "complexity",
        "best_practices",
    ]

    for row in rows:
        model = row.get("model", "").strip()
        if not model:
            continue
        if model not in agg:
            agg[model] = {"count": 0.0}
            for k in keys:
                agg[model][k] = 0.0

        agg[model]["count"] += 1.0
        for k in keys:
            try:
                val = float(row.get(k, "0") or 0)
            except ValueError:
                val = 0.0
            agg[model][k] += val

    # Convert sums to averages
    for model, stats in agg.items():
        count = stats.get("count", 1.0) or 1.0
        for k in keys:
            stats[k] = stats[k] / count

    return agg


def plot_simple_bar(models: List[str], values: List[float], title: str, ylabel: str, output_name: str) -> None:
    """Plot a simple bar chart: one bar per model."""
    if not models:
        print(f"No data to plot for {title}")
        return

    x = range(len(models))
    plt.figure(figsize=(6, 4))
    bars = plt.bar(x, values, width=0.6)

    for i, v in enumerate(values):
        plt.text(
            i,
            v,
            f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.xticks(x, [m.upper() for m in models])
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = ROOT_DIR / output_name
    plt.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")
    plt.close()


def plot_quality_components(model_stats: Dict[str, Dict[str, float]]) -> None:
    """Plot code quality sub-dimensions by model as grouped bars."""
    if not model_stats:
        print("No data to plot for quality components")
        return

    models = sorted(model_stats.keys())
    components = ["structure", "error_handling", "documentation", "complexity", "best_practices"]

    x = range(len(components))
    bar_width = 0.8 / max(len(models), 1)

    plt.figure(figsize=(10, 5))

    for idx, model in enumerate(models):
        offsets = [i + idx * bar_width for i in x]
        vals = [model_stats[model].get(comp, 0.0) for comp in components]
        plt.bar(offsets, vals, width=bar_width, label=model.upper())

        for ox, v in zip(offsets, vals):
            plt.text(
                ox,
                v,
                f"{v:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.xticks(
        [i + (len(models) - 1) * bar_width / 2 for i in x],
        ["Structure", "Error\nHandling", "Docs", "Complexity", "Best\nPractices"],
    )
    plt.ylabel("Code Quality Sub-score (0-100)")
    plt.title("Code Quality Components by Model")
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = ROOT_DIR / "model_avg_quality_components.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")
    plt.close()


def main() -> None:
    rows = load_scores(CSV_PATH)
    if not rows:
        return

    model_stats = aggregate_by_model(rows)
    models = sorted(model_stats.keys())

    # Overall average per model
    overall_vals = [model_stats[m]["overall"] for m in models]
    plot_simple_bar(
        models,
        overall_vals,
        title="Overall Average Score by Model",
        ylabel="Overall Score (0-100)",
        output_name="model_avg_overall.png",
    )

    # Robustness average per model
    robust_vals = [model_stats[m]["robustness"] for m in models]
    plot_simple_bar(
        models,
        robust_vals,
        title="Robustness Average Score by Model",
        ylabel="Robustness Score (0-100)",
        output_name="model_avg_robustness.png",
    )

    # Code quality components (structure, error_handling, etc.)
    plot_quality_components(model_stats)


if __name__ == "__main__":
    main()


