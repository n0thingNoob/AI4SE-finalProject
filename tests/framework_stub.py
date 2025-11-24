"""
FrameworkStub: Mock all framework APIs for testing environment
"""
import math
from typing import Any, Dict, List, Optional, Union
from enum import Enum


# Mock framework enum types
class AlgoStrategyType(Enum):
    SECURITY = "SECURITY"


class GlobalType(Enum):
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"


class THType(Enum):
    ALL = "ALL"
    RTH = "RTH"
    ETH = "ETH"


class BarType(Enum):
    D1 = "D1"
    H1 = "H1"
    M1 = "M1"


class DataType(Enum):
    CLOSE = "CLOSE"
    OPEN = "OPEN"
    HIGH = "HIGH"
    LOW = "LOW"
    VOLUME = "VOLUME"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class TSType(Enum):
    RTH = "RTH"
    ETH = "ETH"


class OrdType(Enum):
    LMT = "LMT"
    MKT = "MKT"


# Mock StrategyBase base class
class StrategyBase:
    """Strategy base class placeholder"""
    pass


class FrameworkStub:
    """
    Stub implementation of framework APIs for testing environment
    Records all API calls and alert behaviors
    """
    
    def __init__(self):
        self.alerts: List[str] = []
        self.orders: List[Dict[str, Any]] = []
        self.declared_strategy_type: Optional[AlgoStrategyType] = None
        self.declared_symbols: List[str] = []
        self.variables: Dict[str, Any] = {}
        
        # Mock market data
        self._price_data: Dict[str, float] = {}
        self._position_data: Dict[str, int] = {}
        self._indicator_data: Dict[str, Dict[str, float]] = {}
        
        # Default test data
        self._default_symbol = "TEST_SYMBOL"
        self._default_price = 100.0
        
    def reset(self):
        """Reset all state"""
        self.alerts.clear()
        self.orders.clear()
        self.declared_strategy_type = None
        self.declared_symbols.clear()
        self.variables.clear()
        self._price_data.clear()
        self._position_data.clear()
        self._indicator_data.clear()
    
    # ========== Framework API Implementation ==========
    
    def declare_strategy_type(self, strategy_type: AlgoStrategyType):
        """Declare strategy type"""
        self.declared_strategy_type = strategy_type
    
    def declare_trig_symbol(self) -> str:
        """Declare trigger symbol"""
        symbol = self._default_symbol
        if symbol not in self.declared_symbols:
            self.declared_symbols.append(symbol)
        return symbol
    
    def show_variable(self, default_value: Union[int, float, str], var_type: GlobalType) -> Union[int, float, str]:
        """Show variable (returns default value)"""
        return default_value
    
    def current_price(self, symbol: str, price_type: THType) -> Optional[float]:
        """Get current price"""
        if symbol in self._price_data:
            return self._price_data[symbol]
        return self._default_price
    
    def set_price(self, symbol: str, price: Optional[float]):
        """Set price (for testing)"""
        self._price_data[symbol] = price
    
    def ma(self, symbol: str, period: int, bar_type: BarType, 
           data_type: Optional[DataType] = None, select: int = 1,
           session_type: Optional[THType] = None) -> Optional[float]:
        """Moving average"""
        key = f"{symbol}_ma_{period}_{bar_type.value}"
        if key in self._indicator_data:
            return self._indicator_data[key].get("value")
        # Default return a reasonable value
        return 100.0
    
    def set_ma(self, symbol: str, period: int, bar_type: BarType, value: Optional[float]):
        """Set MA value (for testing)"""
        key = f"{symbol}_ma_{period}_{bar_type.value}"
        if key not in self._indicator_data:
            self._indicator_data[key] = {}
        self._indicator_data[key]["value"] = value
    
    def rsi(self, symbol: str, period: int, bar_type: BarType,
            select: int = 1) -> Optional[float]:
        """RSI indicator"""
        key = f"{symbol}_rsi_{period}_{bar_type.value}"
        if key in self._indicator_data:
            return self._indicator_data[key].get("value")
        # Default return a reasonable value
        return 50.0
    
    def set_rsi(self, symbol: str, period: int, bar_type: BarType, value: Optional[float]):
        """Set RSI value (for testing)"""
        key = f"{symbol}_rsi_{period}_{bar_type.value}"
        if key not in self._indicator_data:
            self._indicator_data[key] = {}
        self._indicator_data[key]["value"] = value
    
    def position_holding_qty(self, symbol: str) -> int:
        """Get position holding quantity"""
        return self._position_data.get(symbol, 0)
    
    def set_position(self, symbol: str, qty: int):
        """Set position (for testing)"""
        self._position_data[symbol] = qty
    
    def bid(self, symbol: str, level: int = 1) -> Optional[float]:
        """Get bid price"""
        price = self.current_price(symbol, THType.ALL)
        if price is not None:
            return price * 0.999  # Slightly below current price
        return None
    
    def ask(self, symbol: str, level: int = 1) -> Optional[float]:
        """Get ask price"""
        price = self.current_price(symbol, THType.ALL)
        if price is not None:
            return price * 1.001  # Slightly above current price
        return None
    
    def max_qty_to_buy_on_margin(self, symbol: str, price: float, order_type: OrdType) -> Optional[int]:
        """Get maximum quantity to buy on margin"""
        # Mock return a reasonable value
        return 10000
    
    def place_limit(self, symbol: str, price: float, qty: int, side: OrderSide,
                   time_in_force: TimeInForce, order_trade_session_type: TSType):
        """Place limit order"""
        order = {
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "side": side.value,
            "time_in_force": time_in_force.value,
            "order_trade_session_type": order_trade_session_type.value
        }
        self.orders.append(order)
    
    def alert(self, content: str):
        """Send alert"""
        self.alerts.append(content)
    
    def get_alerts(self) -> List[str]:
        """Get all alerts"""
        return self.alerts.copy()
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        return self.orders.copy()


# Global stub instance
_stub_instance: Optional[FrameworkStub] = None


def get_stub() -> FrameworkStub:
    """Get global stub instance"""
    global _stub_instance
    if _stub_instance is None:
        _stub_instance = FrameworkStub()
    return _stub_instance


def reset_stub():
    """Reset global stub"""
    global _stub_instance
    if _stub_instance is not None:
        _stub_instance.reset()

