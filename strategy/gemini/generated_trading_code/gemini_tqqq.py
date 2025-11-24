class Strategy(StrategyBase):
    def initialize(self):
        # 1. Define Strategy Type
        declare_strategy_type(AlgoStrategyType.SECURITY)
        
        # 2. Setup Symbol & Parameters
        self.trigger_symbols()
        self.global_variables()

    # ------------------------------------------------------------------
    # MANDATORY COMPILER FIX
    # ------------------------------------------------------------------
    def custom_indicator(self):
        """
        Required by the Moomoo Algo environment to validate class structure.
        Must return an empty list when indicators are calculated dynamically.
        """
        return []

    def trigger_symbols(self):
        # Defaults to TQQQ, but allows UI selection
        self.target_symbol = declare_trig_symbol()

    def global_variables(self):
        """
        Maps JSON Parameters to UI Variables
        """
        # Position Sizing
        self.qty = show_variable(100, GlobalType.INT)
        
        # Indicators
        self.sma_period = show_variable(200, GlobalType.INT) # Long-term trend floor
        self.rsi_period = show_variable(14, GlobalType.INT)
        
        # Logic Thresholds
        self.rsi_entry_limit = show_variable(35, GlobalType.INT) # Deep dip < 35
        self.rsi_exit_limit = show_variable(65, GlobalType.INT)  # Mean reversion exit > 65
        
        # Risk Management (Variables exposed for UI adjustment)
        self.stop_loss_pct = show_variable(0.10, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.20, GlobalType.FLOAT)

    def handle_data(self):
        """
        Main Execution Loop
        """
        # ---------------------------------------------------------
        # 1. Data Fetching & Validation
        # ---------------------------------------------------------
        
        # Fetch Current Price
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)
        
        # Fetch SMA(200) - Long Term Trend Filter
        # select=2: Previous Completed Bar (Critical for stability)
        sma_val = ma(
            symbol=self.target_symbol, 
            period=self.sma_period, 
            bar_type=BarType.D1, 
            data_type=DataType.CLOSE, 
            select=2, 
            session_type=THType.RTH
        )
        
        # Fetch RSI(14) - Volatility/Dip Detector
        # CRITICAL: RSI does not accept 'data_type' or 'session_type' arguments
        rsi_val = rsi(
            symbol=self.target_symbol, 
            period=self.rsi_period, 
            bar_type=BarType.D1, 
            select=2
        )

        # Safety Check: Abort if any data is missing
        if curr_price is None or sma_val is None or rsi_val is None:
            return

        # ---------------------------------------------------------
        # 2. Position State
        # ---------------------------------------------------------
        curr_qty = position_holding_qty(symbol=self.target_symbol)

        # ---------------------------------------------------------
        # 3. Exit Logic (Priority: Protect Capital)
        # Conditions: RSI Overheated (>65) OR Trend Broken (< SMA200)
        # ---------------------------------------------------------
        if curr_qty > 0:
            cond_overheated = rsi_val > self.rsi_exit_limit
            cond_trend_break = curr_price < sma_val
            
            if cond_overheated or cond_trend_break:
                # Aggressive Exit: Use Bid Level 5 to ensure fill
                sell_p = bid(symbol=self.target_symbol, level=5)
                
                place_limit(
                    symbol=self.target_symbol, 
                    price=sell_p, 
                    qty=curr_qty, 
                    side=OrderSide.SELL, 
                    time_in_force=TimeInForce.DAY, 
                    order_trade_session_type=TSType.RTH
                )
                return # Halt processing for this tick

        # ---------------------------------------------------------
        # 4. Entry Logic
        # Conditions: Bullish Trend (> SMA200) AND Deep Dip (< RSI 35)
        # ---------------------------------------------------------
        elif curr_qty == 0:
            cond_bull_trend = curr_price > sma_val
            cond_deep_dip = rsi_val < self.rsi_entry_limit
            
            if cond_bull_trend and cond_deep_dip:
                # Aggressive Entry: Use Ask Level 5
                buy_p = ask(symbol=self.target_symbol, level=5)
                
                # Margin Safety Check
                max_buy = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol, 
                    price=buy_p, 
                    order_type=OrdType.LMT
                )
                
                # Sizing Logic
                final_qty = self.qty
                if final_qty > max_buy:
                    final_qty = max_buy
                
                if final_qty > 0:
                    place_limit(
                        symbol=self.target_symbol, 
                        price=buy_p, 
                        qty=final_qty, 
                        side=OrderSide.BUY, 
                        time_in_force=TimeInForce.DAY, 
                        order_trade_session_type=TSType.RTH
                    )