"""
Test Data Generator: Generate boundary and random test data
"""
import math
import random
from typing import List, Dict, Optional, Any

try:
    from tests.framework_stub import FrameworkStub, BarType
except ImportError:
    from framework_stub import FrameworkStub, BarType


class TestDataGenerator:
    """Generate various boundary and exception test data"""
    
    @staticmethod
    def get_boundary_test_cases() -> List[Dict[str, Any]]:
        """
        Generate boundary test cases
        
        Returns:
            List of test cases, each containing price, ma, rsi, etc.
        """
        test_cases = []
        
        # Basic boundary values
        boundary_values = [
            None,                    # None value
            float('nan'),            # NaN
            float('inf'),            # Positive infinity
            float('-inf'),           # Negative infinity
            0.0,                     # Zero
            -1.0,                    # Negative number
            1e10,                    # Very large value
            -1e10,                   # Very small value
            1e-10,                   # Positive number close to zero
            -1e-10,                  # Negative number close to zero
        ]
        
        # Generate combinations of price, MA, RSI
        for price in boundary_values:
            for ma_val in boundary_values:
                for rsi_val in boundary_values:
                    # Skip meaningless combinations (e.g., RSI negative or > 100)
                    if rsi_val is not None and not math.isnan(rsi_val) and not math.isinf(rsi_val):
                        if rsi_val < 0 or rsi_val > 100:
                            continue
                    
                    test_cases.append({
                        "name": f"price={price}, ma={ma_val}, rsi={rsi_val}",
                        "price": price,
                        "ma": ma_val,
                        "rsi": rsi_val
                    })
        
        # Add some common boundary combinations
        common_cases = [
            {"name": "normal_values", "price": 100.0, "ma": 95.0, "rsi": 50.0},
            {"name": "price_none", "price": None, "ma": 95.0, "rsi": 50.0},
            {"name": "ma_none", "price": 100.0, "ma": None, "rsi": 50.0},
            {"name": "rsi_none", "price": 100.0, "ma": 95.0, "rsi": None},
            {"name": "all_none", "price": None, "ma": None, "rsi": None},
            {"name": "price_nan", "price": float('nan'), "ma": 95.0, "rsi": 50.0},
            {"name": "price_inf", "price": float('inf'), "ma": 95.0, "rsi": 50.0},
            {"name": "price_neg_inf", "price": float('-inf'), "ma": 95.0, "rsi": 50.0},
            {"name": "price_zero", "price": 0.0, "ma": 95.0, "rsi": 50.0},
            {"name": "price_negative", "price": -10.0, "ma": 95.0, "rsi": 50.0},
            {"name": "ma_nan", "price": 100.0, "ma": float('nan'), "rsi": 50.0},
            {"name": "rsi_nan", "price": 100.0, "ma": 95.0, "rsi": float('nan')},
            {"name": "rsi_boundary_0", "price": 100.0, "ma": 95.0, "rsi": 0.0},
            {"name": "rsi_boundary_100", "price": 100.0, "ma": 95.0, "rsi": 100.0},
            {"name": "rsi_negative", "price": 100.0, "ma": 95.0, "rsi": -10.0},
            {"name": "rsi_over_100", "price": 100.0, "ma": 95.0, "rsi": 150.0},
        ]
        
        test_cases.extend(common_cases)
        return test_cases
    
    @staticmethod
    def get_random_test_cases(count: int = 100, seed: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate random test cases
        
        Args:
            count: Number of test cases to generate
            seed: Random seed
            
        Returns:
            List of test cases
        """
        if seed is not None:
            random.seed(seed)
        
        test_cases = []
        for i in range(count):
            # Generate random but reasonable price (10-1000)
            price = random.uniform(10.0, 1000.0)
            
            # MA fluctuates around price (±20%)
            ma = price * random.uniform(0.8, 1.2)
            
            # RSI between 0-100
            rsi = random.uniform(0.0, 100.0)
            
            # Occasionally insert None or exception values
            if random.random() < 0.1:  # 10% probability
                price = None
            if random.random() < 0.1:
                ma = None
            if random.random() < 0.1:
                rsi = None
            if random.random() < 0.05:  # 5% probability
                price = float('nan')
            if random.random() < 0.05:
                ma = float('nan')
            
            test_cases.append({
                "name": f"random_case_{i+1}",
                "price": price,
                "ma": ma,
                "rsi": rsi
            })
        
        return test_cases
    
    @staticmethod
    def apply_test_data_to_stub(stub: FrameworkStub, symbol: str, test_case: Dict[str, Any]):
        """
        Apply test data to stub
        
        Args:
            stub: FrameworkStub instance
            symbol: Trading symbol
            test_case: Test case data
        """
        # Set price
        stub.set_price(symbol, test_case.get("price"))
        
        # Set MA (assuming period=100, bar_type=D1)
        stub.set_ma(symbol, 100, BarType.D1, test_case.get("ma"))
        stub.set_ma(symbol, 50, BarType.D1, test_case.get("ma"))
        stub.set_ma(symbol, 20, BarType.D1, test_case.get("ma"))
        stub.set_ma(symbol, 200, BarType.D1, test_case.get("ma"))
        stub.set_ma(symbol, 1, BarType.D1, test_case.get("ma"))
        
        # Set RSI (assuming period=14, bar_type=D1)
        stub.set_rsi(symbol, 14, BarType.D1, test_case.get("rsi"))
