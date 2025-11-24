"""
Strategy Loader: Auto-discover and load strategy modules
"""
import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Type, Any


def find_strategy_files(root_dir: str = "strategy") -> List[Path]:
    """
    Recursively find all strategy files (.py files)
    
    Args:
        root_dir: Strategy root directory
        
    Returns:
        List of strategy file paths
    """
    root_path = Path(root_dir)
    if not root_path.exists():
        return []
    
    strategy_files = []
    for py_file in root_path.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" not in str(py_file) and "test" not in py_file.name.lower():
            # Check if file is actually Python code (not JSON)
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    # Skip JSON files (start with { or [)
                    if not (first_line.startswith('{') or first_line.startswith('[')):
                        strategy_files.append(py_file)
            except Exception:
                # If can't read, skip it
                continue
    
    return sorted(strategy_files)


def load_strategy_class(file_path: Path) -> Tuple[Optional[Type[Any]], Optional[str], Optional[str]]:
    """
    Load Strategy class from file
    
    Args:
        file_path: Strategy file path
        
    Returns:
        (Strategy class, module name, error message)
    """
    try:
        # Generate unique module name
        module_name = f"strategy_{file_path.stem}_{id(file_path)}"
        
        # Read file content
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None, None, f"Failed to create module spec: {file_path}"
        
        # Load module
        module = importlib.util.module_from_spec(spec)
        
        # Inject framework stub into module namespace
        try:
            from tests.framework_stub import (
                StrategyBase, AlgoStrategyType, GlobalType, THType, BarType, DataType,
                OrderSide, TimeInForce, TSType, OrdType, get_stub
            )
        except ImportError:
            from framework_stub import (
                StrategyBase, AlgoStrategyType, GlobalType, THType, BarType, DataType,
                OrderSide, TimeInForce, TSType, OrdType, get_stub
            )
        
        # Inject framework APIs into module
        stub = get_stub()
        module.StrategyBase = StrategyBase
        module.AlgoStrategyType = AlgoStrategyType
        module.GlobalType = GlobalType
        module.THType = THType
        module.BarType = BarType
        module.DataType = DataType
        module.OrderSide = OrderSide
        module.TimeInForce = TimeInForce
        module.TSType = TSType
        module.OrdType = OrdType
        
        # Inject framework functions
        module.declare_strategy_type = stub.declare_strategy_type
        module.declare_trig_symbol = stub.declare_trig_symbol
        module.show_variable = stub.show_variable
        module.current_price = stub.current_price
        module.ma = stub.ma
        module.rsi = stub.rsi
        module.position_holding_qty = stub.position_holding_qty
        module.bid = stub.bid
        module.ask = stub.ask
        module.max_qty_to_buy_on_margin = stub.max_qty_to_buy_on_margin
        module.place_limit = stub.place_limit
        module.alert = stub.alert
        
        # Execute module
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find Strategy class
        strategy_class = None
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                obj.__module__ == module_name and
                issubclass(obj, StrategyBase) and
                obj != StrategyBase):
                if name == "Strategy":
                    strategy_class = obj
                    break
                elif strategy_class is None:
                    # If Strategy not found, record first class as fallback
                    strategy_class = obj
        
        if strategy_class is None:
            # Find first class (even if not Strategy)
            classes = [obj for name, obj in inspect.getmembers(module, inspect.isclass)
                      if obj.__module__ == module_name and obj != StrategyBase]
            if classes:
                first_class = classes[0]
                return None, None, f"Strategy class not found, found class: {first_class.__name__}. Please ensure class name is Strategy."
            return None, None, "No strategy class found"
        
        if strategy_class.__name__ != "Strategy":
            return None, None, f"Found class name is not 'Strategy', but '{strategy_class.__name__}'. Please ensure class name is Strategy."
        
        return strategy_class, module_name, None
        
    except Exception as e:
        return None, None, f"Loading failed: {str(e)}"


def get_strategy_info(file_path: Path) -> dict:
    """
    Get strategy file information
    
    Returns:
        Dictionary containing file path, relative path, etc.
    """
    try:
        rel_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = str(file_path)
    return {
        "file_path": str(file_path),
        "relative_path": rel_path,
        "name": file_path.stem
    }
