"""
Robustness Test Module: Test strategy behavior under boundary and exception conditions
"""
import math
import traceback
from typing import Type, Any, Dict, List, Tuple, Optional

try:
    from tests.framework_stub import FrameworkStub, get_stub, reset_stub
    from tests.test_data_generator import TestDataGenerator
except ImportError:
    from framework_stub import FrameworkStub, get_stub, reset_stub
    from test_data_generator import TestDataGenerator


class RobustnessTestResult:
    """Test result"""
    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0
    
    def add_error(self, error_msg: str):
        """Add error"""
        self.passed = False
        self.errors.append(error_msg)
        self.fail_count += 1
    
    def add_warning(self, warning_msg: str):
        """Add warning"""
        self.warnings.append(warning_msg)
    
    def add_pass(self):
        """Record pass"""
        self.pass_count += 1
    
    def __str__(self) -> str:
        result = []
        result.append(f"Total tests: {self.test_count}")
        result.append(f"Passed: {self.pass_count}")
        result.append(f"Failed: {self.fail_count}")
        if self.errors:
            result.append("\nErrors:")
            for err in self.errors:
                result.append(f"  - {err}")
        if self.warnings:
            result.append("\nWarnings:")
            for warn in self.warnings:
                result.append(f"  - {warn}")
        return "\n".join(result)


def test_initialize(strategy_class: Type[Any], stub: FrameworkStub) -> Tuple[bool, Optional[str]]:
    """
    Test initialize() method
    
    Args:
        strategy_class: Strategy class
        stub: FrameworkStub instance
        
    Returns:
        (success, error message)
    """
    try:
        stub.reset()
        strategy = strategy_class()
        strategy.initialize()
        return True, None
    except Exception as e:
        error_msg = f"initialize() failed: {str(e)}\n{traceback.format_exc()}"
        return False, error_msg


def test_handle_data_boundary(strategy_class: Type[Any], stub: FrameworkStub, 
                               symbol: str) -> RobustnessTestResult:
    """
    Test handle_data() behavior under boundary conditions
    
    Args:
        strategy_class: Strategy class
        stub: FrameworkStub instance
        symbol: Trading symbol
        
    Returns:
        Test result
    """
    result = RobustnessTestResult()
    test_cases = TestDataGenerator.get_boundary_test_cases()
    result.test_count = len(test_cases)
    
    for test_case in test_cases:
        try:
            # Reset stub and strategy instance
            stub.reset()
            strategy = strategy_class()
            strategy.initialize()
            
            # Apply test data
            TestDataGenerator.apply_test_data_to_stub(stub, symbol, test_case)
            
            # Set position (test different position states)
            for position_qty in [0, 100, -100]:
                stub.set_position(symbol, position_qty)
                
                # Try to execute handle_data
                try:
                    strategy.handle_data()
                    result.add_pass()
                except Exception as e:
                    # Record error but don't fail immediately (some boundary values may cause exceptions normally)
                    error_msg = f"Test case '{test_case['name']}' (position={position_qty}) execution failed: {str(e)}"
                    result.add_error(error_msg)
                    
        except Exception as e:
            error_msg = f"Test case '{test_case['name']}' setup failed: {str(e)}"
            result.add_error(error_msg)
    
    return result


def test_handle_data_random(strategy_class: Type[Any], stub: FrameworkStub,
                            symbol: str, count: int = 100) -> RobustnessTestResult:
    """
    Test handle_data() behavior under random data
    
    Args:
        strategy_class: Strategy class
        stub: FrameworkStub instance
        symbol: Trading symbol
        count: Number of random tests
        
    Returns:
        Test result
    """
    result = RobustnessTestResult()
    test_cases = TestDataGenerator.get_random_test_cases(count=count, seed=42)
    result.test_count = len(test_cases)
    
    for test_case in test_cases:
        try:
            # Reset stub and strategy instance
            stub.reset()
            strategy = strategy_class()
            strategy.initialize()
            
            # Apply test data
            TestDataGenerator.apply_test_data_to_stub(stub, symbol, test_case)
            
            # Random position state
            import random
            position_qty = random.choice([0, 50, 100, 200, -50])
            stub.set_position(symbol, position_qty)
            
            # Try to execute handle_data
            try:
                strategy.handle_data()
                result.add_pass()
            except Exception as e:
                error_msg = f"Random test '{test_case['name']}' execution failed: {str(e)}"
                result.add_error(error_msg)
                
        except Exception as e:
            error_msg = f"Random test '{test_case['name']}' setup failed: {str(e)}"
            result.add_error(error_msg)
    
    return result


def test_strategy_robustness(strategy_class: Type[Any], strategy_name: str) -> Dict[str, Any]:
    """
    Execute complete robustness test for strategy
    
    Args:
        strategy_class: Strategy class
        strategy_name: Strategy name
        
    Returns:
        Test result dictionary
    """
    stub = get_stub()
    stub.reset()
    
    # Initialize strategy to get symbol
    try:
        strategy = strategy_class()
        strategy.initialize()
        symbol = stub.declared_symbols[0] if stub.declared_symbols else "TEST_SYMBOL"
    except Exception as e:
        return {
            "strategy_name": strategy_name,
            "initialize_passed": False,
            "initialize_error": str(e),
            "boundary_tests": None,
            "random_tests": None
        }
    
    # Test initialize
    init_passed, init_error = test_initialize(strategy_class, stub)
    
    # Test boundary conditions
    boundary_result = test_handle_data_boundary(strategy_class, stub, symbol)
    
    # Test random conditions
    random_result = test_handle_data_random(strategy_class, stub, symbol, count=50)
    
    return {
        "strategy_name": strategy_name,
        "initialize_passed": init_passed,
        "initialize_error": init_error,
        "boundary_tests": {
            "test_count": boundary_result.test_count,
            "pass_count": boundary_result.pass_count,
            "fail_count": boundary_result.fail_count,
            "errors": boundary_result.errors[:10]  # Keep only first 10 errors
        },
        "random_tests": {
            "test_count": random_result.test_count,
            "pass_count": random_result.pass_count,
            "fail_count": random_result.fail_count,
            "errors": random_result.errors[:10]
        }
    }
