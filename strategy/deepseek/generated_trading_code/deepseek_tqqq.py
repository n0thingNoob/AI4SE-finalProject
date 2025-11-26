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
        self.sma_period = show_variable(50, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)
        self.rsi_entry_threshold = show_variable(42, GlobalType.INT)
        self.rsi_exit_threshold = show_variable(68, GlobalType.INT)
        
    def handle_data(self):
        # Fetch current market data
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)
        if curr_price is None:
            return
            
        # Fetch indicator values
        sma_val = ma(
            symbol=self.target_symbol,
            period=self.sma_period,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )
        
        rsi_val = rsi(
            symbol=self.target_symbol,
            period=self.rsi_period,
            bar_type=BarType.D1,
            select=2
        )
        
        # Validate indicator data
        if sma_val is None or rsi_val is None:
            return
            
        # Check current position
        curr_qty = position_holding_qty(symbol=self.target_symbol)
        
        # EXIT LOGIC (Priority 1) - Check if we need to sell
        if curr_qty > 0:
            # Exit conditions based on RSI and SMA only (signal-based exits)
            exit_signal = (rsi_val > self.rsi_exit_threshold or curr_price < sma_val)
            
            if exit_signal:
                # Aggressive sell at bid price
                sell_price = bid(symbol=self.target_symbol, level=5)
                if sell_price:
                    place_limit(
                        symbol=self.target_symbol,
                        price=sell_price,
                        qty=curr_qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY,
                        order_trade_session_type=TSType.RTH
                    )
                return
                
        # ENTRY LOGIC (Priority 2) - Check if we should buy
        elif curr_qty == 0:
            # Entry condition: Price above SMA AND RSI below threshold
            entry_signal = (curr_price > sma_val and rsi_val < self.rsi_entry_threshold)
            
            if entry_signal:
                # Check maximum buyable quantity
                max_buyable = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol,
                    price=curr_price,
                    order_type=OrdType.LMT
                )
                
                # Use minimum of desired quantity and max buyable
                buy_qty = min(self.qty, max_buyable) if max_buyable else self.qty
                
                if buy_qty > 0:
                    # Aggressive buy at ask price
                    buy_price = ask(symbol=self.target_symbol, level=5)
                    if buy_price:
                        place_limit(
                            symbol=self.target_symbol,
                            price=buy_price,
                            qty=buy_qty,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY,
                            order_trade_session_type=TSType.RTH
                        )