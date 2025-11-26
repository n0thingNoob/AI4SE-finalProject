class Strategy(StrategyBase):
    def custom_indicator(self):
        return None
    
    def initialize(self):
        declare_strategy_type(AlgoStrategyType.SECURITY)
        self.trigger_symbols()
        self.global_variables()
        
    def trigger_symbols(self):
        self.target_symbol = declare_trig_symbol()
        
    def global_variables(self):
        self.qty = show_variable(2000, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)
        self.rsi_oversold = show_variable(30, GlobalType.INT)
        self.rsi_overbought = show_variable(65, GlobalType.INT)
        self.sma_period = show_variable(50, GlobalType.INT)
        self.stop_loss_pct = show_variable(0.07, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.12, GlobalType.FLOAT)
        
        # Track entry price for stop loss calculation
        self.entry_price = 0
        
    def handle_data(self):
        try:
            # Fetch current market data - use ALL price type (correct)
            curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)
            
            if curr_price is None:
                return
                
            # Fetch indicator values - use select=1 (previous bar) instead of select=2
            rsi_val = rsi(
                symbol=self.target_symbol,
                period=self.rsi_period,
                bar_type=BarType.D1,
                select=1  # Changed from 2 to 1 for more recent data
            )
            
            sma_50 = ma(
                symbol=self.target_symbol,
                period=self.sma_period,
                bar_type=BarType.D1,
                data_type=DataType.CLOSE,
                select=1,  # Changed from 2 to 1
                session_type=THType.RTH
            )
            
            # Additional safety: price above short-term MA as support
            sma_20 = ma(
                symbol=self.target_symbol,
                period=20,
                bar_type=BarType.D1,
                data_type=DataType.CLOSE,
                select=1,  # Changed from 2 to 1
                session_type=THType.RTH
            )
            
            # Validate we have all required data
            if (rsi_val is None or sma_50 is None or sma_20 is None):
                return
                
            # Check current position
            curr_qty = position_holding_qty(symbol=self.target_symbol)
            
            # EXIT LOGIC (Priority 1)
            if curr_qty > 0:
                # Calculate P&L percentages
                price_change_pct = (curr_price - self.entry_price) / self.entry_price
                
                # Exit Conditions
                exit_condition_1 = rsi_val > self.rsi_overbought
                exit_condition_2 = curr_price > sma_50
                exit_condition_3 = price_change_pct <= -self.stop_loss_pct
                exit_condition_4 = price_change_pct >= self.take_profit_pct
                
                if exit_condition_1 or exit_condition_2 or exit_condition_3 or exit_condition_4:
                    sell_price = bid(symbol=self.target_symbol, level=1)  # Use level 1
                    if sell_price:
                        place_limit(
                            symbol=self.target_symbol,
                            price=sell_price,
                            qty=curr_qty,
                            side=OrderSide.SELL,
                            time_in_force=TimeInForce.DAY,
                            order_trade_session_type=TSType.RTH
                        )
                        self.entry_price = 0
                    return
            
            # ENTRY LOGIC (Priority 2)
            if curr_qty == 0:
                # Entry Conditions
                entry_condition_1 = rsi_val < self.rsi_oversold
                entry_condition_2 = curr_price > sma_20
                # entry_condition_1 = rsi_val < 35  # Relaxed from 30 to 35
                # entry_condition_2 = True  # Remove SMA20 condition for testing
                
                if entry_condition_1 and entry_condition_2:
                    # Check maximum buyable quantity
                    max_buyable = max_qty_to_buy_on_margin(
                        symbol=self.target_symbol,
                        price=curr_price,
                        order_type=OrdType.LMT
                    )
                    
                    buy_qty = min(self.qty, max_buyable)
                    
                    if buy_qty > 0:
                        buy_price = ask(symbol=self.target_symbol, level=1)  # Use level 1
                        if buy_price:
                            place_limit(
                                symbol=self.target_symbol,
                                price=buy_price,
                                qty=buy_qty,
                                side=OrderSide.BUY,
                                time_in_force=TimeInForce.DAY,
                                order_trade_session_type=TSType.RTH
                            )
                            self.entry_price = buy_price
        except Exception as e:
            # Handle any errors gracefully
            pass