"""
Main test file: Auto-discover and test all generated strategies
"""
import sys
import csv
from pathlib import Path
from typing import List, Dict, Any, List as _List

# Add project root and tests directory to path
project_root = Path(__file__).parent.parent
tests_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tests_dir))

# Import test modules
from strategy_loader import find_strategy_files, load_strategy_class, get_strategy_info
from robustness_tests import test_strategy_robustness
from framework_stub import reset_stub
from code_quality_scorer import CodeQualityScorer


def get_model_from_path(file_path: Path) -> str:
    """Extract model name from file path (gemini or gpt)"""
    path_str = str(file_path).lower()
    if "gemini" in path_str:
        return "gemini"
    elif "gpt" in path_str or "chatgpt" in path_str:
        return "gpt"
    elif "deepseek" in path_str:
        return "deepseek"
    else:
        return "unknown"


def run_all_tests() -> Dict[str, Any]:
    """
    Run tests for all strategies
    
    Returns:
        Test results summary
    """
    # Find all strategy files
    strategy_files = find_strategy_files("strategy")
    
    if not strategy_files:
        print("No strategy files found")
        return {"total": 0, "results": []}
    
    print(f"Found {len(strategy_files)} strategy files\n")
    
    results = []
    csv_rows: _List[Dict[str, Any]] = []
    total_passed = 0
    total_failed = 0
    
    # Group results by model
    # Keys must match get_model_from_path() return values
    model_results = {"gemini": [], "gpt": [], "deepseek": [], "unknown": []}
    
    for strategy_file in strategy_files:
        try:
            rel_path = strategy_file.relative_to(Path.cwd())
        except ValueError:
            rel_path = str(strategy_file)
        print(f"Testing strategy: {rel_path}")
        print("-" * 80)
        
        # Load strategy class
        strategy_class, module_name, error = load_strategy_class(strategy_file)
        
        if error:
            print(f"[ERROR] Load failed: {error}\n")
            results.append({
                "file": str(strategy_file),
                "status": "load_failed",
                "error": error
            })
            total_failed += 1
            continue
        
        if strategy_class is None:
            print(f"[ERROR] Strategy class not found\n")
            results.append({
                "file": str(strategy_file),
                "status": "class_not_found",
                "error": error or "Strategy class not found"
            })
            total_failed += 1
            continue
        
        # Execute robustness tests
        strategy_info = get_strategy_info(strategy_file)
        test_result = test_strategy_robustness(strategy_class, strategy_info["name"])
        
        # Read source code for quality scoring
        try:
            with open(strategy_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            source_code = ""
            print(f"[WARNING] Could not read source code: {e}")
        
        # Calculate code quality scores
        scorer = CodeQualityScorer()
        scores = scorer.score_strategy(strategy_class, source_code, test_result)
        
        # Print results
        if test_result["initialize_passed"]:
            print("[PASS] initialize() test passed")
        else:
            print(f"[FAIL] initialize() test failed: {test_result['initialize_error']}")
        
        if test_result["boundary_tests"]:
            bt = test_result["boundary_tests"]
            print(f"Boundary tests: {bt['pass_count']}/{bt['test_count']} passed, {bt['fail_count']} failed")
            if bt['fail_count'] > 0 and bt['errors']:
                print(f"  First few errors:")
                for err in bt['errors'][:3]:
                    print(f"    - {err[:100]}...")
        
        if test_result["random_tests"]:
            rt = test_result["random_tests"]
            print(f"Random tests: {rt['pass_count']}/{rt['test_count']} passed, {rt['fail_count']} failed")
            if rt['fail_count'] > 0 and rt['errors']:
                print(f"  First few errors:")
                for err in rt['errors'][:3]:
                    print(f"    - {err[:100]}...")
        
        # Print scoring results
        print("\n" + "=" * 80)
        print("CODE QUALITY & ROBUSTNESS SCORING")
        print("=" * 80)
        print(f"Overall Score: {scores['overall']}/100 (Grade: {scores['grade']})")
        print(f"  Robustness Score: {scores['robustness']}/100")
        quality = scores.get('quality', {})
        print(f"  Code Quality Score: {quality.get('overall', 0)}/100")
        print(f"    - Structure: {quality.get('structure', 0)}/100")
        print(f"    - Error Handling: {quality.get('error_handling', 0)}/100")
        print(f"    - Documentation: {quality.get('documentation', 0)}/100")
        print(f"    - Complexity: {quality.get('complexity', 0)}/100")
        print(f"    - Best Practices: {quality.get('best_practices', 0)}/100")
        print("=" * 80)
        
        # Determine overall pass/fail
        overall_passed = (
            test_result["initialize_passed"] and
            test_result["boundary_tests"]["fail_count"] == 0 and
            test_result["random_tests"]["fail_count"] == 0
        )
        
        if overall_passed:
            print("[PASS] Overall test passed\n")
            total_passed += 1
        else:
            print("[FAIL] Overall test failed\n")
            total_failed += 1
        
        test_result["file"] = str(strategy_file)
        test_result["status"] = "passed" if overall_passed else "failed"
        test_result["scores"] = scores
        
        # Group by model
        model = get_model_from_path(strategy_file)
        if "scores" in test_result:
            model_results[model].append(test_result)
        
        results.append(test_result)

        # Collect CSV row for this strategy
        quality_scores = scores.get("quality", {})
        csv_rows.append(
            {
                "model": model,
                "file": str(strategy_file),
                "strategy_name": strategy_info["name"],
                "overall": scores.get("overall", 0.0),
                "robustness": scores.get("robustness", 0.0),
                "quality_overall": quality_scores.get("overall", 0.0),
                "structure": quality_scores.get("structure", 0.0),
                "error_handling": quality_scores.get("error_handling", 0.0),
                "documentation": quality_scores.get("documentation", 0.0),
                "complexity": quality_scores.get("complexity", 0.0),
                "best_practices": quality_scores.get("best_practices", 0.0),
            }
        )
        
        # Reset stub
        reset_stub()
    
    # Summary (console)
    print("=" * 80)
    print(f"Test Summary:")
    print(f"  Total strategies: {len(strategy_files)}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    
    # Overall average scores
    scored_results = [r for r in results if "scores" in r]
    if scored_results:
        avg_overall = sum(r["scores"]["overall"] for r in scored_results) / len(scored_results)
        avg_robustness = sum(r["scores"]["robustness"] for r in scored_results) / len(scored_results)
        avg_quality = sum(r["scores"]["quality"]["overall"] for r in scored_results) / len(scored_results)
        print(f"\nOverall Average Scores:")
        print(f"  Overall: {avg_overall:.2f}/100")
        print(f"  Robustness: {avg_robustness:.2f}/100")
        print(f"  Code Quality: {avg_quality:.2f}/100")
    
    # Model-specific statistics
    print("\n" + "=" * 80)
    print("MODEL-SPECIFIC SCORING SUMMARY")
    print("=" * 80)
    
    for model_name in ["gemini", "gpt", "deepseek"]:
        model_strategies = model_results[model_name]
        if not model_strategies:
            continue
        
        scored = [r for r in model_strategies if "scores" in r]
        if not scored:
            continue
        
        print(f"\n{model_name.upper()} Model:")
        print(f"  Total strategies: {len(model_strategies)}")
        print(f"  Passed: {sum(1 for r in model_strategies if r.get('status') == 'passed')}")
        print(f"  Failed: {sum(1 for r in model_strategies if r.get('status') == 'failed')}")
        
        # Display individual file scores
        print(f"\n  Individual File Scores:")
        for result in scored:
            file_name = Path(result["file"]).name
            scores = result["scores"]
            print(f"    {file_name}:")
            print(f"      Overall: {scores['overall']:.2f}/100")
            print(f"      Robustness: {scores['robustness']:.2f}/100")
            print(f"      Code Quality: {scores['quality']['overall']:.2f}/100")
        
        # Calculate averages
        avg_overall = sum(r["scores"]["overall"] for r in scored) / len(scored)
        avg_robustness = sum(r["scores"]["robustness"] for r in scored) / len(scored)
        avg_quality = sum(r["scores"]["quality"]["overall"] for r in scored) / len(scored)
        
        # Calculate detailed quality averages
        avg_structure = sum(r["scores"]["quality"]["structure"] for r in scored) / len(scored)
        avg_error_handling = sum(r["scores"]["quality"]["error_handling"] for r in scored) / len(scored)
        avg_documentation = sum(r["scores"]["quality"]["documentation"] for r in scored) / len(scored)
        avg_complexity = sum(r["scores"]["quality"]["complexity"] for r in scored) / len(scored)
        avg_best_practices = sum(r["scores"]["quality"]["best_practices"] for r in scored) / len(scored)
        
        print(f"\n  Average Scores:")
        print(f"    Overall: {avg_overall:.2f}/100")
        print(f"    Robustness: {avg_robustness:.2f}/100")
        print(f"    Code Quality: {avg_quality:.2f}/100")
        print(f"      - Structure: {avg_structure:.2f}/100")
        print(f"      - Error Handling: {avg_error_handling:.2f}/100")
        print(f"      - Documentation: {avg_documentation:.2f}/100")
        print(f"      - Complexity: {avg_complexity:.2f}/100")
        print(f"      - Best Practices: {avg_best_practices:.2f}/100")
        
        # Total scores (sum of all strategies)
        max_score = 100.0 * len(scored)
        total_overall = sum(r["scores"]["overall"] for r in scored)
        total_robustness = sum(r["scores"]["robustness"] for r in scored)
        total_quality = sum(r["scores"]["quality"]["overall"] for r in scored)
        print(f"\n  Total Scores (Sum of {len(scored)} strategies, max: {max_score:.2f}):")
        print(f"    Overall: {total_overall:.2f}/{max_score:.2f}")
        print(f"    Robustness: {total_robustness:.2f}/{max_score:.2f}")
        print(f"    Code Quality: {total_quality:.2f}/{max_score:.2f}")
    
    print("\n" + "=" * 80)

    # Write the same summary and model statistics to a report file
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("Test Summary:")
    report_lines.append(f"  Total strategies: {len(strategy_files)}")
    report_lines.append(f"  Passed: {total_passed}")
    report_lines.append(f"  Failed: {total_failed}")

    if scored_results:
        report_lines.append("")
        report_lines.append("Overall Average Scores:")
        report_lines.append(f"  Overall: {avg_overall:.2f}/100")
        report_lines.append(f"  Robustness: {avg_robustness:.2f}/100")
        report_lines.append(f"  Code Quality: {avg_quality:.2f}/100")

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("MODEL-SPECIFIC SCORING SUMMARY")
    report_lines.append("=" * 80)

    for model_name in ["gemini", "gpt", "deepseek"]:
        model_strategies = model_results[model_name]
        if not model_strategies:
            continue

        scored = [r for r in model_strategies if "scores" in r]
        if not scored:
            continue

        report_lines.append("")
        report_lines.append(f"{model_name.upper()} Model:")
        report_lines.append(f"  Total strategies: {len(model_strategies)}")
        report_lines.append(f"  Passed: {sum(1 for r in model_strategies if r.get('status') == 'passed')}")
        report_lines.append(f"  Failed: {sum(1 for r in model_strategies if r.get('status') == 'failed')}")

        report_lines.append("")
        report_lines.append("  Individual File Scores:")
        for result in scored:
            file_name = Path(result["file"]).name
            scores = result["scores"]
            report_lines.append(f"    {file_name}:")
            report_lines.append(f"      Overall: {scores['overall']:.2f}/100")
            report_lines.append(f"      Robustness: {scores['robustness']:.2f}/100")
            report_lines.append(f"      Code Quality: {scores['quality']['overall']:.2f}/100")

        # Recompute averages for this model
        avg_overall_model = sum(r["scores"]["overall"] for r in scored) / len(scored)
        avg_robustness_model = sum(r["scores"]["robustness"] for r in scored) / len(scored)
        avg_quality_model = sum(r["scores"]["quality"]["overall"] for r in scored) / len(scored)

        avg_structure = sum(r["scores"]["quality"]["structure"] for r in scored) / len(scored)
        avg_error_handling = sum(r["scores"]["quality"]["error_handling"] for r in scored) / len(scored)
        avg_documentation = sum(r["scores"]["quality"]["documentation"] for r in scored) / len(scored)
        avg_complexity = sum(r["scores"]["quality"]["complexity"] for r in scored) / len(scored)
        avg_best_practices = sum(r["scores"]["quality"]["best_practices"] for r in scored) / len(scored)

        report_lines.append("")
        report_lines.append("  Average Scores:")
        report_lines.append(f"    Overall: {avg_overall_model:.2f}/100")
        report_lines.append(f"    Robustness: {avg_robustness_model:.2f}/100")
        report_lines.append(f"    Code Quality: {avg_quality_model:.2f}/100")
        report_lines.append(f"      - Structure: {avg_structure:.2f}/100")
        report_lines.append(f"      - Error Handling: {avg_error_handling:.2f}/100")
        report_lines.append(f"      - Documentation: {avg_documentation:.2f}/100")
        report_lines.append(f"      - Complexity: {avg_complexity:.2f}/100")
        report_lines.append(f"      - Best Practices: {avg_best_practices:.2f}/100")

        max_score_model = 100.0 * len(scored)
        total_overall_model = sum(r["scores"]["overall"] for r in scored)
        total_robustness_model = sum(r["scores"]["robustness"] for r in scored)
        total_quality_model = sum(r["scores"]["quality"]["overall"] for r in scored)

        report_lines.append("")
        report_lines.append(f"  Total Scores (Sum of {len(scored)} strategies, max: {max_score_model:.2f}):")
        report_lines.append(f"    Overall: {total_overall_model:.2f}/{max_score_model:.2f}")
        report_lines.append(f"    Robustness: {total_robustness_model:.2f}/{max_score_model:.2f}")
        report_lines.append(f"    Code Quality: {total_quality_model:.2f}/{max_score_model:.2f}")

    report_lines.append("")
    report_lines.append("=" * 80)

    tests_dir = Path(__file__).parent
    report_path = tests_dir / "test_results.txt"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\nDetailed report written to {report_path}")

    # Write per-strategy scores to CSV for visualization
    if csv_rows:
        csv_path = tests_dir / "strategy_scores.csv"
        fieldnames = [
            "model",
            "file",
            "strategy_name",
            "overall",
            "robustness",
            "quality_overall",
            "structure",
            "error_handling",
            "documentation",
            "complexity",
            "best_practices",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Per-strategy scores written to {csv_path}")

    return {
        "total": len(strategy_files),
        "passed": total_passed,
        "failed": total_failed,
        "results": results,
        "model_results": model_results
    }


if __name__ == "__main__":
    results = run_all_tests()
    # Return non-zero exit code if there are failures
    sys.exit(0 if results["failed"] == 0 else 1)
