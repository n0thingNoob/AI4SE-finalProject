class Strategy(StrategyBase):
    def custom_indicator(self):
        # Mandatory convention function required by Moomoo
        # Even if unused, it MUST exist inside the class.
        return None
    
    def initialize(self):
        declare_strategy_type(AlgoStrategyType.SECURITY)
        self.trigger_symbols()
        self.global_variables()
        
    def trigger_symbols(self):
        self.target_symbol = declare_trig_symbol()
        
    def global_variables(self):
        self.qty = show_variable(2000, GlobalType.INT)
        self.ma_period = show_variable(100, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)
        self.rsi_oversold = show_variable(45, GlobalType.INT)
        self.rsi_overbought = show_variable(70, GlobalType.INT)
        self.stop_loss_pct = show_variable(0.05, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.15, GlobalType.FLOAT)
        # Track entry price manually since position_holding_cost is not available
        self.entry_price = 0.0
        
    def handle_data(self):
        # Fetch current market data
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)
        
        # Fetch indicator values
        sma_100 = ma(
            symbol=self.target_symbol,
            period=self.ma_period,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )
        
        rsi_14 = rsi(
            symbol=self.target_symbol,
            period=self.rsi_period,
            bar_type=BarType.D1,
            select=2
        )
        
        # Validate data before proceeding
        if curr_price is None or sma_100 is None or rsi_14 is None:
            return
            
        # Get current position
        curr_qty = position_holding_qty(symbol=self.target_symbol)
        
        # EXIT LOGIC (Priority 1) - Check if we need to sell
        if curr_qty > 0:
            # Use manually tracked entry price for stop loss/take profit
            if self.entry_price > 0:
                exit_condition_1 = rsi_14 > self.rsi_overbought
                exit_condition_2 = curr_price < sma_100
                exit_condition_3 = curr_price >= self.entry_price * (1 + self.take_profit_pct)
                exit_condition_4 = curr_price <= self.entry_price * (1 - self.stop_loss_pct)
                
                if exit_condition_1 or exit_condition_2 or exit_condition_3 or exit_condition_4:
                    # Sell at bid price (aggressive)
                    sell_price = bid(symbol=self.target_symbol, level=5)
                    if sell_price is not None:
                        place_limit(
                            symbol=self.target_symbol,
                            price=sell_price,
                            qty=curr_qty,
                            side=OrderSide.SELL,
                            time_in_force=TimeInForce.DAY,
                            order_trade_session_type=TSType.RTH
                        )
                        # Reset entry price after selling
                        self.entry_price = 0.0
                    return
                
        # ENTRY LOGIC (Priority 2) - Check if we should buy
        if curr_qty == 0:
            entry_condition_1 = curr_price > sma_100
            entry_condition_2 = rsi_14 < self.rsi_oversold
            
            if entry_condition_1 and entry_condition_2:
                # Check max buy capacity
                max_buy_qty = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol,
                    price=curr_price,
                    order_type=OrdType.LMT
                )
                
                # Use minimum of desired quantity and max allowed
                buy_qty = min(self.qty, max_buy_qty)
                
                if buy_qty > 0:
                    # Buy at ask price (aggressive)
                    buy_price = ask(symbol=self.target_symbol, level=5)
                    if buy_price is not None:
                        place_limit(
                            symbol=self.target_symbol,
                            price=buy_price,
                            qty=buy_qty,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY,
                            order_trade_session_type=TSType.RTH
                        )
                        # Store entry price for future stop loss/take profit calculations
                        self.entry_price = buy_price