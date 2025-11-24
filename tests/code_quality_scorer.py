"""
Code Quality Scorer: Evaluate strategy code quality and robustness
"""
import ast
import inspect
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json


class CodeQualityScorer:
    """Score code quality and robustness"""
    
    def __init__(self):
        self.quality_weights = {
            "structure": 0.20,      # Code structure and organization
            "error_handling": 0.25,  # Error handling and validation
            "documentation": 0.15,   # Docstrings and comments
            "complexity": 0.15,      # Code complexity
            "best_practices": 0.25   # Best practices and conventions
        }
    
    def score_strategy(self, strategy_class: type, source_code: str, 
                      robustness_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a strategy's code quality and robustness
        
        Args:
            strategy_class: Strategy class
            source_code: Source code of the strategy
            robustness_result: Robustness test results
            
        Returns:
            Scoring results dictionary
        """
        scores = {}
        
        # Robustness score (0-100)
        robustness_score = self._calculate_robustness_score(robustness_result)
        scores["robustness"] = robustness_score
        
        # Code quality score (0-100)
        quality_scores = self._calculate_quality_scores(strategy_class, source_code)
        scores["quality"] = quality_scores
        
        # Overall score (weighted average)
        overall_score = (
            robustness_score * 0.4 +  # Robustness is 40%
            quality_scores["overall"] * 0.6  # Quality is 60%
        )
        scores["overall"] = round(overall_score, 2)
        
        # Grade assignment
        scores["grade"] = self._assign_grade(overall_score)
        
        return scores
    
    def _calculate_robustness_score(self, robustness_result: Dict[str, Any]) -> float:
        """Calculate robustness score from test results"""
        if not robustness_result.get("initialize_passed", False):
            return 0.0
        
        boundary_tests = robustness_result.get("boundary_tests", {})
        random_tests = robustness_result.get("random_tests", {})
        
        boundary_pass_rate = 0.0
        if boundary_tests.get("test_count", 0) > 0:
            # Calculate pass rate, but cap at 1.0 (100%)
            pass_count = boundary_tests.get("pass_count", 0)
            test_count = boundary_tests.get("test_count", 1)
            boundary_pass_rate = min(pass_count / test_count, 1.0)
        
        random_pass_rate = 0.0
        if random_tests.get("test_count", 0) > 0:
            pass_count = random_tests.get("pass_count", 0)
            test_count = random_tests.get("test_count", 1)
            random_pass_rate = min(pass_count / test_count, 1.0)
        
        # Weighted average: boundary 60%, random 40%
        robustness_score = (boundary_pass_rate * 0.6 + random_pass_rate * 0.4) * 100
        return round(min(robustness_score, 100.0), 2)
    
    def _calculate_quality_scores(self, strategy_class: type, source_code: str) -> Dict[str, float]:
        """Calculate code quality scores"""
        scores = {
            "structure": 0.0,
            "error_handling": 0.0,
            "documentation": 0.0,
            "complexity": 0.0,
            "best_practices": 0.0
        }
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return {**scores, "overall": 0.0}
        
        # Structure score
        scores["structure"] = self._score_structure(strategy_class, tree)
        
        # Error handling score
        scores["error_handling"] = self._score_error_handling(tree)
        
        # Documentation score
        scores["documentation"] = self._score_documentation(strategy_class, tree)
        
        # Complexity score
        scores["complexity"] = self._score_complexity(tree)
        
        # Best practices score
        scores["best_practices"] = self._score_best_practices(tree, source_code)
        
        # Calculate overall quality score
        overall = sum(
            scores[key] * self.quality_weights[key] 
            for key in scores.keys()
        )
        scores["overall"] = round(overall, 2)
        
        return scores
    
    def _score_structure(self, strategy_class: type, tree: ast.AST) -> float:
        """Score code structure (0-100)"""
        score = 50.0  # Base score
        
        # Check if required methods exist
        required_methods = ["initialize", "handle_data"]
        class_methods = []
        for name, _ in inspect.getmembers(strategy_class):
            if inspect.ismethod(getattr(strategy_class, name, None)) or \
               inspect.isfunction(getattr(strategy_class, name, None)):
                class_methods.append(name)
        
        for method in required_methods:
            if method in class_methods:
                score += 15.0
        
        # Check for custom_indicator method (optional but recommended)
        if "custom_indicator" in class_methods:
            score += 10.0
        
        # Check for proper class structure
        if len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]) > 0:
            score += 10.0
        
        return min(score, 100.0)
    
    def _score_error_handling(self, tree: ast.AST) -> float:
        """Score error handling (0-100)"""
        score = 30.0  # Base score
        
        # Count try-except blocks
        try_blocks = len([node for node in ast.walk(tree) if isinstance(node, ast.Try)])
        score += min(try_blocks * 15.0, 40.0)
        
        # Check for None checks
        none_checks = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and comparator.value is None:
                        none_checks += 1
                    elif isinstance(comparator, ast.NameConstant) and comparator.value is None:
                        none_checks += 1
        
        score += min(none_checks * 3.0, 30.0)
        
        return min(score, 100.0)
    
    def _score_documentation(self, strategy_class: type, tree: ast.AST) -> float:
        """Score documentation (0-100)"""
        score = 0.0
        
        # Check class docstring
        class_docstrings = [
            node for node in ast.walk(tree) 
            if isinstance(node, ast.ClassDef) and ast.get_docstring(node)
        ]
        if class_docstrings:
            score += 30.0
        
        # Check method docstrings
        method_docstrings = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and ast.get_docstring(node)
        ]
        score += min(len(method_docstrings) * 10.0, 70.0)
        
        return min(score, 100.0)
    
    def _score_complexity(self, tree: ast.AST) -> float:
        """Score code complexity (lower complexity = higher score)"""
        # Count cyclomatic complexity indicators
        complexity_indicators = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                complexity_indicators += 1
            elif isinstance(node, ast.BoolOp):
                complexity_indicators += len(node.values) - 1
        
        # Lower complexity = higher score
        # 0-5: 100, 6-10: 80, 11-15: 60, 16-20: 40, 21+: 20
        if complexity_indicators <= 5:
            score = 100.0
        elif complexity_indicators <= 10:
            score = 80.0
        elif complexity_indicators <= 15:
            score = 60.0
        elif complexity_indicators <= 20:
            score = 40.0
        else:
            score = 20.0
        
        return score
    
    def _score_best_practices(self, tree: ast.AST, source_code: str) -> float:
        """Score best practices (0-100)"""
        score = 50.0  # Base score
        
        # Check for magic numbers (negative)
        magic_numbers = len([
            node for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
            and node.value not in [0, 1, -1, 2, 100]  # Common exceptions
        ])
        score -= min(magic_numbers * 2.0, 20.0)
        
        # Check for variable naming (snake_case)
        # This is a simplified check
        if "_" in source_code:  # Indicates snake_case usage
            score += 10.0
        
        # Check for proper return statements
        return_nodes = len([node for node in ast.walk(tree) if isinstance(node, ast.Return)])
        if return_nodes > 0:
            score += 10.0
        
        # Check for early returns (good practice)
        early_returns = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                for child in ast.walk(node):
                    if isinstance(child, ast.Return):
                        early_returns += 1
        score += min(early_returns * 5.0, 20.0)
        
        return max(0.0, min(score, 100.0))
    
    def _assign_grade(self, score: float) -> str:
        """Assign letter grade based on score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def get_detailed_report(self, scores: Dict[str, Any], 
                           robustness_result: Dict[str, Any]) -> str:
        """Generate detailed scoring report"""
        report = []
        report.append("=" * 80)
        report.append("CODE QUALITY & ROBUSTNESS SCORING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall score
        report.append(f"Overall Score: {scores['overall']}/100 (Grade: {scores['grade']})")
        report.append("")
        
        # Robustness breakdown
        report.append("ROBUSTNESS SCORE:")
        report.append(f"  Score: {scores['robustness']}/100")
        if robustness_result.get("boundary_tests"):
            bt = robustness_result["boundary_tests"]
            report.append(f"  Boundary Tests: {bt.get('pass_count', 0)}/{bt.get('test_count', 0)} passed")
        if robustness_result.get("random_tests"):
            rt = robustness_result["random_tests"]
            report.append(f"  Random Tests: {rt.get('pass_count', 0)}/{rt.get('test_count', 0)} passed")
        report.append("")
        
        # Quality breakdown
        report.append("CODE QUALITY SCORE:")
        quality = scores.get("quality", {})
        report.append(f"  Overall Quality: {quality.get('overall', 0)}/100")
        report.append(f"  Structure: {quality.get('structure', 0)}/100")
        report.append(f"  Error Handling: {quality.get('error_handling', 0)}/100")
        report.append(f"  Documentation: {quality.get('documentation', 0)}/100")
        report.append(f"  Complexity: {quality.get('complexity', 0)}/100")
        report.append(f"  Best Practices: {quality.get('best_practices', 0)}/100")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        recommendations = self._generate_recommendations(scores, robustness_result)
        if recommendations:
            for rec in recommendations:
                report.append(f"  - {rec}")
        else:
            report.append("  No major issues found. Code quality is good!")
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _generate_recommendations(self, scores: Dict[str, Any], 
                                 robustness_result: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if scores["robustness"] < 80:
            recommendations.append("Improve robustness by adding more error handling and validation")
        
        quality = scores.get("quality", {})
        
        if quality.get("error_handling", 0) < 60:
            recommendations.append("Add more try-except blocks and None checks for better error handling")
        
        if quality.get("documentation", 0) < 50:
            recommendations.append("Add docstrings to classes and methods for better documentation")
        
        if quality.get("complexity", 0) < 60:
            recommendations.append("Reduce code complexity by breaking down large functions")
        
        if quality.get("best_practices", 0) < 60:
            recommendations.append("Follow Python best practices: use constants instead of magic numbers")
        
        if quality.get("structure", 0) < 70:
            recommendations.append("Improve code structure: ensure all required methods are implemented")
        
        return recommendations

