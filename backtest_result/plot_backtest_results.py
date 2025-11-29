"""
Plot backtest results from annualized_return.csv and total_return.csv
as bar charts.

Usage:
    python backtest_result/plot_backtest_results.py
"""

import csv
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt


ROOT_DIR = Path(__file__).resolve().parent


def load_return_csv(path: Path) -> Dict[str, Dict[str, float]]:
    """
    Load a CSV file with structure:
        Stock\Model, Chat-GPT, Gemini, DeepSeek
        NVDA,11.70%,24.37%,13.64%
    Returns:
        { stock: { model: value_float, ... }, ... }
    """
    results: Dict[str, Dict[str, float]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return results

        # First column is Stock\Model, remaining are models
        models = [h.strip() for h in header[1:]]

        for row in reader:
            if not row or not row[0].strip():
                continue
            stock = row[0].strip()
            values: Dict[str, float] = {}
            for model, raw in zip(models, row[1:]):
                raw = (raw or "").strip()
                if raw.endswith("%"):
                    raw = raw[:-1]
                try:
                    values[model] = float(raw)
                except ValueError:
                    continue
            results[stock] = values

    return results


def plot_bar_chart(
    data: Dict[str, Dict[str, float]],
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    """Plot grouped bar chart for given data."""
    if not data:
        print(f"No data to plot for {title}")
        return

    stocks: List[str] = list(data.keys())
    # Assume all stocks share the same model set
    all_models: List[str] = sorted(
        {m for values in data.values() for m in values.keys()}
    )

    x = range(len(stocks))
    bar_width = 0.8 / max(len(all_models), 1)

    plt.figure(figsize=(8, 5))

    for idx, model in enumerate(all_models):
        vals = [data[stock].get(model, 0.0) for stock in stocks]
        offsets = [i + idx * bar_width for i in x]
        bars = plt.bar(offsets, vals, width=bar_width, label=model)

        # Add value labels on top of each bar
        for ox, v in zip(offsets, vals):
            plt.text(
                ox,
                v,
                f"{v:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.xticks(
        [i + (len(all_models) - 1) * bar_width / 2 for i in x],
        stocks,
    )
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Saved figure to {output_path}")
    plt.close()


def main() -> None:
    annualized_path = ROOT_DIR / "annualized_return.csv"
    total_path = ROOT_DIR / "total_return.csv"

    annualized_data = load_return_csv(annualized_path)
    total_data = load_return_csv(total_path)

    plot_bar_chart(
        annualized_data,
        title="Annualized Return by Model and Stock",
        ylabel="Annualized Return (%)",
        output_path=ROOT_DIR / "annualized_return.png",
    )

    plot_bar_chart(
        total_data,
        title="Total Return by Model and Stock",
        ylabel="Total Return (%)",
        output_path=ROOT_DIR / "total_return.png",
    )


if __name__ == "__main__":
    main()


