class Strategy(StrategyBase):
    def initialize(self):
        # 1. Define Strategy Type
        declare_strategy_type(AlgoStrategyType.SECURITY)
        
        # 2. Setup Symbol & Parameters
        self.trigger_symbols()
        self.global_variables()

    # ------------------------------------------------------------------
    # MANDATORY INTERFACE FIX
    # ------------------------------------------------------------------
    def custom_indicator(self):
        """
        Required by the environment to validate the class structure.
        Returns an empty list as we calculate indicators dynamically.
        """
        return []

    def trigger_symbols(self):
        # User selects TSLA in the UI
        self.target_symbol = declare_trig_symbol()

    def global_variables(self):
        """
        Maps JSON Parameters to UI Variables
        """
        # Position Sizing
        self.qty = show_variable(100, GlobalType.INT)
        
        # Indicator Periods
        self.sma_period = show_variable(100, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)
        
        # Logic Thresholds
        self.rsi_buy_threshold = show_variable(40, GlobalType.INT)  # Entry < 40
        self.rsi_sell_threshold = show_variable(70, GlobalType.INT) # Exit > 70
        
        # Risk Management (Placeholders for UI awareness)
        self.stop_loss_pct = show_variable(0.08, GlobalType.FLOAT)
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
        
        # Fetch SMA(100) - Trend Filter
        # select=2 ensures we use the previous COMPLETED bar to avoid repainting
        sma_val = ma(
            symbol=self.target_symbol, 
            period=self.sma_period, 
            bar_type=BarType.D1, 
            data_type=DataType.CLOSE, 
            select=2, 
            session_type=THType.RTH
        )
        
        # Fetch RSI(14) - Momentum
        # Note: RSI does not accept data_type or session_type
        rsi_val = rsi(
            symbol=self.target_symbol, 
            period=self.rsi_period, 
            bar_type=BarType.D1, 
            select=2
        )

        # Safety Check: Do not proceed if data is missing
        if curr_price is None or sma_val is None or rsi_val is None:
            return

        # ---------------------------------------------------------
        # 2. Position State
        # ---------------------------------------------------------
        curr_qty = position_holding_qty(symbol=self.target_symbol)

        # ---------------------------------------------------------
        # 3. Exit Logic (Priority: Close existing before opening new)
        # Condition: RSI > 70 OR Trend Breakdown (Price < SMA)
        # ---------------------------------------------------------
        if curr_qty > 0:
            cond_overbought = rsi_val > self.rsi_sell_threshold
            cond_trend_fail = curr_price < sma_val
            
            if cond_overbought or cond_trend_fail:
                # Aggressive Exit: Bid Level 5
                sell_price = bid(symbol=self.target_symbol, level=5)
                
                place_limit(
                    symbol=self.target_symbol, 
                    price=sell_price, 
                    qty=curr_qty, 
                    side=OrderSide.SELL, 
                    time_in_force=TimeInForce.DAY, 
                    order_trade_session_type=TSType.RTH
                )
                return # Stop processing this tick

        # ---------------------------------------------------------
        # 4. Entry Logic
        # Condition: Uptrend (Price > SMA) AND Dip (RSI < 40)
        # ---------------------------------------------------------
        elif curr_qty == 0:
            cond_uptrend = curr_price > sma_val
            cond_dip = rsi_val < self.rsi_buy_threshold
            
            if cond_uptrend and cond_dip:
                # Aggressive Entry: Ask Level 5
                buy_price = ask(symbol=self.target_symbol, level=5)
                
                # Margin Check
                max_buy = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol, 
                    price=buy_price, 
                    order_type=OrdType.LMT
                )
                
                # Determine final quantity (User request vs Max allowed)
                final_qty = self.qty
                if final_qty > max_buy:
                    final_qty = max_buy
                
                if final_qty > 0:
                    place_limit(
                        symbol=self.target_symbol, 
                        price=buy_price, 
                        qty=final_qty, 
                        side=OrderSide.BUY, 
                        time_in_force=TimeInForce.DAY, 
                        order_trade_session_type=TSType.RTH
                    )