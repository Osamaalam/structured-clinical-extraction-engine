"""Evaluation script — compares extraction output against ground truth.

Usage:
    python scripts/evaluate.py [--output results.json] [--ground-truth data/ground_truth.xlsx]

This script reads your extraction output (JSON) and the ground truth spreadsheet,
then computes accuracy metrics per measure and overall.
"""

import argparse
import json
import sys
from pathlib import Path

import openpyxl
import pandas as pd


def load_ground_truth(xlsx_path: str) -> pd.DataFrame:
    """Load ground truth from the all_pdfs_outcome_measures sheet."""
    df = pd.read_excel(xlsx_path, sheet_name="all_pdfs_outcome_measures")
    # Forward-fill article_id since the spreadsheet merges cells
    df["article_id"] = df["article_id"].ffill()
    return df


def load_predictions(json_path: str) -> pd.DataFrame:
    """Load extraction predictions from JSON output."""
    with open(json_path) as f:
        data = json.load(f)

    # Flatten: expected format is {article_id: [measure_result_dicts]}
    rows = []
    for article_id, results in data.items():
        for result in results:
            result["article_id"] = article_id
            rows.append(result)

    return pd.DataFrame(rows)


def evaluate_numeric_match(predicted: float, expected: float, tolerance: float = 0.01) -> bool:
    """Check if a predicted numeric value matches expected within tolerance."""
    if predicted is None or expected is None:
        return predicted is None and expected is None
    return abs(predicted - expected) <= abs(expected * tolerance)


def evaluate(ground_truth: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    """Compare predictions against ground truth."""
    metrics = {
        "total_expected_rows": len(ground_truth),
        "total_predicted_rows": len(predictions),
        "per_measure": {},
        "per_article": {},
        "field_accuracy": {},
    }

    # Group by measure
    for measure_name in ground_truth["measure_definition_short_name"].unique():
        gt_measure = ground_truth[ground_truth["measure_definition_short_name"] == measure_name]
        pred_measure = predictions[predictions.get("measure_definition_short_name", pd.Series()) == measure_name]

        metrics["per_measure"][measure_name] = {
            "expected_rows": len(gt_measure),
            "predicted_rows": len(pred_measure),
            "recall": len(pred_measure) / len(gt_measure) if len(gt_measure) > 0 else 0,
        }

    # Group by article
    for article_id in ground_truth["article_id"].unique():
        gt_article = ground_truth[ground_truth["article_id"] == article_id]
        pred_article = predictions[predictions.get("article_id", pd.Series()) == article_id]

        metrics["per_article"][article_id] = {
            "expected_rows": len(gt_article),
            "predicted_rows": len(pred_article),
        }

    # Field-level accuracy for matched rows
    numeric_fields = ["primary_val", "dispersion_val_1", "dispersion_val_2", "p_value"]
    categorical_fields = ["stat_type", "dispersion_type", "p_operator", "timepoint_unit"]

    for field in numeric_fields + categorical_fields:
        correct = 0
        total = 0

        for _, gt_row in ground_truth.iterrows():
            # Find matching prediction (same article + measure + arm)
            mask = predictions.get("article_id", pd.Series()) == gt_row["article_id"]
            mask &= predictions.get("measure_definition_short_name", pd.Series()) == gt_row["measure_definition_short_name"]
            if pd.notna(gt_row.get("study_arm")):
                mask &= predictions.get("study_arm", pd.Series()) == gt_row["study_arm"]

            matches = predictions[mask]
            if len(matches) == 0:
                total += 1
                continue

            pred_row = matches.iloc[0]
            total += 1

            gt_val = gt_row.get(field)
            pred_val = pred_row.get(field)

            if field in numeric_fields:
                if evaluate_numeric_match(pred_val, gt_val):
                    correct += 1
            else:
                if str(pred_val).upper().strip() == str(gt_val).upper().strip():
                    correct += 1

        metrics["field_accuracy"][field] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total > 0 else 0,
        }

    # Overall score
    field_accuracies = [v["accuracy"] for v in metrics["field_accuracy"].values()]
    metrics["overall_field_accuracy"] = sum(field_accuracies) / len(field_accuracies) if field_accuracies else 0

    row_recalls = [v["recall"] for v in metrics["per_measure"].values()]
    metrics["overall_row_recall"] = sum(row_recalls) / len(row_recalls) if row_recalls else 0

    return metrics


def print_report(metrics: dict):
    """Print a human-readable evaluation report."""
    print("\n" + "=" * 60)
    print("OUTCOME EXTRACTION EVALUATION REPORT")
    print("=" * 60)

    print(f"\nRows: {metrics['total_predicted_rows']} predicted / {metrics['total_expected_rows']} expected")
    print(f"Overall Row Recall: {metrics['overall_row_recall']:.1%}")
    print(f"Overall Field Accuracy: {metrics['overall_field_accuracy']:.1%}")

    print("\n--- Per Measure ---")
    for measure, data in metrics["per_measure"].items():
        print(f"  {measure}: {data['predicted_rows']}/{data['expected_rows']} rows (recall: {data['recall']:.1%})")

    print("\n--- Per Article ---")
    for article, data in metrics["per_article"].items():
        print(f"  {article}: {data['predicted_rows']}/{data['expected_rows']} rows")

    print("\n--- Field Accuracy ---")
    for field, data in metrics["field_accuracy"].items():
        print(f"  {field}: {data['correct']}/{data['total']} ({data['accuracy']:.1%})")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evaluate extraction output against ground truth")
    parser.add_argument("--output", default="extraction_output.json", help="Path to extraction output JSON")
    parser.add_argument("--ground-truth", default="data/ground_truth.xlsx", help="Path to ground truth XLSX")
    args = parser.parse_args()

    if not Path(args.output).exists():
        print(f"Error: Output file not found: {args.output}")
        print("Run `python run_extraction.py` first to generate extraction output.")
        sys.exit(1)

    if not Path(args.ground_truth).exists():
        print(f"Error: Ground truth file not found: {args.ground_truth}")
        sys.exit(1)

    ground_truth = load_ground_truth(args.ground_truth)
    predictions = load_predictions(args.output)
    metrics = evaluate(ground_truth, predictions)
    print_report(metrics)

    # Save metrics
    metrics_path = Path(args.output).stem + "_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"\nDetailed metrics saved to: {metrics_path}")


if __name__ == "__main__":
    main()
