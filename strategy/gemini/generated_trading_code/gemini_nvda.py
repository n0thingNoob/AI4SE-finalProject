class Strategy(StrategyBase):
    def initialize(self):
        # 1. Define Strategy Type
        declare_strategy_type(AlgoStrategyType.SECURITY)
        
        # 2. Setup Symbol & Parameters
        self.trigger_symbols()
        self.global_variables()

    def trigger_symbols(self):
        # Default to NVDA, but allow UI selection
        self.target_symbol = declare_trig_symbol()

    def global_variables(self):
        """
        Parameter Mapping from JSON to UI Variables
        """
        # Trading Size
        self.qty = show_variable(100, GlobalType.INT)
        
        # Indicators
        self.sma_period = show_variable(100, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)
        
        # Thresholds
        self.rsi_entry_limit = show_variable(45, GlobalType.INT) # Buy if < 45
        self.rsi_exit_limit = show_variable(70, GlobalType.INT)  # Sell if > 70
        
        # Risk Management (Percentages)
        self.stop_loss_pct = show_variable(0.05, GlobalType.FLOAT) 
        self.take_profit_pct = show_variable(0.15, GlobalType.FLOAT)

    def custom_indicator(self):
        """
        MANDATORY CONVENTION FUNCTION
        Even if empty, this function must exist for the strategy to compile.
        """
        pass

    def handle_data(self):
        """
        Main Loop: Executed on every tick/bar update
        """
        self.trading_logic_invoke()

    def trading_logic_invoke(self):
        # ---------------------------------------------------------
        # 1. Fetch Data & Indicators (Strict API Compliance)
        # ---------------------------------------------------------
        
        # Current Market Price
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)
        
        # SMA(100): D1, Previous Completed Bar (select=2)
        sma_val = ma(
            symbol=self.target_symbol, 
            period=self.sma_period, 
            bar_type=BarType.D1, 
            data_type=DataType.CLOSE, 
            select=2, 
            session_type=THType.RTH
        )
        
        # RSI(14): D1, Previous Completed Bar (select=2)
        # CRITICAL: Do not pass data_type or session_type to RSI
        rsi_val = rsi(
            symbol=self.target_symbol, 
            period=self.rsi_period, 
            bar_type=BarType.D1, 
            select=2
        )

        # Validation: Ensure indicators are ready (not None) before logic
        if curr_price is None or sma_val is None or rsi_val is None:
            return

        # ---------------------------------------------------------
        # 2. Position Management
        # ---------------------------------------------------------
        curr_qty = position_holding_qty(symbol=self.target_symbol)

        # ---------------------------------------------------------
        # 3. Exit Logic (Priority 1)
        # JSON: exit_condition: rsi > 70 or close < sma100
        # ---------------------------------------------------------
        if curr_qty > 0:
            # Condition A: RSI Overbought
            cond_rsi_exit = rsi_val > self.rsi_exit_limit
            
            # Condition B: Trend Breakdown (Price falls below SMA)
            cond_trend_break = curr_price < sma_val
            
            if cond_rsi_exit or cond_trend_break:
                # Aggressive Sell: Use Bid Level 5
                sell_p = bid(symbol=self.target_symbol, level=5)
                
                place_limit(
                    symbol=self.target_symbol, 
                    price=sell_p, 
                    qty=curr_qty, 
                    side=OrderSide.SELL, 
                    time_in_force=TimeInForce.DAY, 
                    order_trade_session_type=TSType.RTH
                )
                return # Exit function after placing order

        # ---------------------------------------------------------
        # 4. Entry Logic (Priority 2)
        # JSON: entry_condition: close > sma100 and rsi < 45
        # ---------------------------------------------------------
        elif curr_qty == 0:
            # Condition A: Bullish Trend (Price > SMA)
            cond_trend_up = curr_price > sma_val
            
            # Condition B: Oversold/Dip (RSI < 45)
            cond_dip = rsi_val < self.rsi_entry_limit
            
            if cond_trend_up and cond_dip:
                # Aggressive Buy: Use Ask Level 5
                buy_p = ask(symbol=self.target_symbol, level=5)
                
                # Risk Check: Max Quantity
                # [Check] Using OrdType.LMT correctly
                max_can_buy = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol, 
                    price=buy_p, 
                    order_type=OrdType.LMT
                )
                
                # Determine final size (User setting vs Margin limit)
                final_qty = self.qty
                if final_qty > max_can_buy:
                    final_qty = max_can_buy
                
                if final_qty > 0:
                    place_limit(
                        symbol=self.target_symbol, 
                        price=buy_p, 
                        qty=final_qty, 
                        side=OrderSide.BUY, 
                        time_in_force=TimeInForce.DAY, 
                        order_trade_session_type=TSType.RTH
                    )