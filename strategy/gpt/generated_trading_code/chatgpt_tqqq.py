class Strategy(StrategyBase):

    def initialize(self):
        # Strategy type
        declare_strategy_type(AlgoStrategyType.SECURITY)

        # Setup
        self.trigger_symbols()
        self.global_variables()

    # ---------------------------------
    # SYMBOL SELECTION
    # ---------------------------------
    def trigger_symbols(self):
        # Allow user to select target in UI
        self.target_symbol = declare_trig_symbol()

    # ---------------------------------
    # PARAMETERS & INTERNAL STATE
    # ---------------------------------
    def global_variables(self):
        # --- User-adjustable parameters (from JSON) ---
        # Position size
        self.qty = show_variable(100, GlobalType.INT)

        # Trend filter: SMA(50)
        self.ma_period = show_variable(50, GlobalType.INT)

        # Bollinger Bands parameters: 20-period, 2 std dev
        self.bb_period = show_variable(20, GlobalType.INT)
        self.bb_dev = show_variable(2.0, GlobalType.FLOAT)

        # RSI parameters
        self.rsi_period = show_variable(14, GlobalType.INT)
        self.rsi_oversold = show_variable(40.0, GlobalType.FLOAT)   # Entry: RSI < 40
        self.rsi_overbought = show_variable(75.0, GlobalType.FLOAT) # Exit: RSI > 75

        # Stop loss / Take profit (as decimal fractions)
        # 0.08 = 8% stop loss, 0.18 = 18% take profit
        self.stop_loss_pct = show_variable(0.08, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.18, GlobalType.FLOAT)

        # --- Internal state (NOT user-facing) ---
        # Track entry price of current position
        self.entry_price = None

        # Rolling window of closes for custom Bollinger Bands
        self.bb_close_window = []

        # To reduce duplicate appends within the same bar (optional safety)
        self.last_close_price = None

    # ---------------------------------
    # HELPER: UPDATE BOLLINGER WINDOW
    # ---------------------------------
    def _update_bbands_window(self, close_price):
        """
        Maintain a rolling window of the last `bb_period` closes.
        No external libraries; simple list-based buffer.
        """
        if close_price is None:
            return

        # Optional guard to avoid repeated identical appends;
        # safe even if handle_data is called multiple times per bar.
        if self.last_close_price is not None and close_price == self.last_close_price:
            # We might still be within same bar; don't double-count.
            return

        self.last_close_price = close_price

        self.bb_close_window.append(close_price)
        if len(self.bb_close_window) > self.bb_period:
            self.bb_close_window.pop(0)

    # ---------------------------------
    # HELPER: COMPUTE BOLLINGER BANDS
    # ---------------------------------
    def _compute_bbands(self):
        """
        Compute Bollinger Bands (middle, upper, lower) from the rolling window.
        Returns (mid, upper, lower) or (None, None, None) if not enough data.
        """
        period = int(self.bb_period)
        if period <= 1 or len(self.bb_close_window) < period:
            return None, None, None

        # Simple average
        window = self.bb_close_window
        n = len(window)
        s = 0.0
        for v in window:
            s += v
        mean = s / n

        # Standard deviation
        ssq = 0.0
        for v in window:
            diff = v - mean
            ssq += diff * diff
        variance = ssq / n
        std = variance ** 0.5

        dev = float(self.bb_dev)
        upper = mean + dev * std
        lower = mean - dev * std

        return mean, upper, lower

    # ---------------------------------
    # MAIN LOGIC
    # ---------------------------------
    def handle_data(self):
        symbol = self.target_symbol

        # -----------------------------
        # 1. Fetch current price & indicators
        # -----------------------------
        close_price = current_price(symbol=symbol, price_type=THType.ALL)

        # Maintain our custom Bollinger window using the latest price
        self._update_bbands_window(close_price)

        # SMA(50) trend filter (using previous completed bar: select=2)
        sma_val = ma(
            symbol=symbol,
            period=int(self.ma_period),
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        # RSI(14) (note: RSI has fewer params; NO data_type/session_type)
        rsi_val = rsi(
            symbol=symbol,
            period=int(self.rsi_period),
            bar_type=BarType.D1,
            select=2
        )

        # Custom Bollinger from rolling window
        bb_mid, bb_upper, bb_lower = self._compute_bbands()

        # If any critical data is missing, skip this tick
        if close_price is None or sma_val is None or rsi_val is None:
            return

        # It's also okay if Bollinger is not ready yet; just skip
        if bb_mid is None or bb_upper is None or bb_lower is None:
            # Not enough history for BB yet
            pass

        # -----------------------------
        # 2. Position info
        # -----------------------------
        curr_qty = position_holding_qty(symbol=symbol)

        # -----------------------------
        # 3. EXIT LOGIC (checked first)
        #    Exit when ANY of:
        #      (1) Close < SMA(50)
        #      (2) RSI > 75
        #      (3) Close >= upper Bollinger Band
        #    OR stop-loss / take-profit triggers
        # -----------------------------
        if curr_qty > 0 and self.entry_price is not None:
            exit_signal = False

            # Indicator-based exit
            if close_price < sma_val:
                exit_signal = True
            if rsi_val > float(self.rsi_overbought):
                exit_signal = True
            if bb_upper is not None and close_price >= bb_upper:
                exit_signal = True

            # Stop-loss / Take-profit exits
            stop_loss_trigger = False
            take_profit_trigger = False

            if self.entry_price is not None:
                stop_loss_level = self.entry_price * (1.0 - float(self.stop_loss_pct))
                take_profit_level = self.entry_price * (1.0 + float(self.take_profit_pct))

                if close_price <= stop_loss_level:
                    stop_loss_trigger = True
                if close_price >= take_profit_level:
                    take_profit_trigger = True

            if exit_signal or stop_loss_trigger or take_profit_trigger:
                # Use aggressive sell at bid(level=5)
                sell_price = bid(symbol=symbol, level=5)
                if sell_price is None:
                    sell_price = close_price

                if sell_price is not None and curr_qty > 0:
                    place_limit(
                        symbol=symbol,
                        price=sell_price,
                        qty=curr_qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY,
                        order_trade_session_type=TSType.RTH
                    )
                    # Reset internal state
                    self.entry_price = None
                # After attempting to exit, return (no new entries in same bar)
                return

        # -----------------------------
        # 4. ENTRY LOGIC (only if flat)
        #    Enter long when ALL of:
        #      (1) Close > SMA(50)
        #      (2) RSI < 40
        #      (3) Close <= lower Bollinger Band
        #      (4) No existing long position
        # -----------------------------
        if curr_qty <= 0:
            # Need Bollinger ready for entry condition
            if bb_lower is None:
                return

            cond_trend = close_price > sma_val
            cond_rsi = rsi_val < float(self.rsi_oversold)
            cond_boll = close_price <= bb_lower

            if cond_trend and cond_rsi and cond_boll:
                # Determine buy price (aggressive at ask level 5)
                buy_price = ask(symbol=symbol, level=5)
                if buy_price is None:
                    buy_price = close_price

                if buy_price is None:
                    return

                # Risk control: don't exceed max marginable quantity
                max_can_buy = max_qty_to_buy_on_margin(
                    symbol=symbol,
                    price=buy_price,
                    order_type=OrdType.LMT
                )

                # Final order size (capped by both user qty and broker limit)
                order_qty = min(int(self.qty), int(max_can_buy))

                if order_qty > 0:
                    place_limit(
                        symbol=symbol,
                        price=buy_price,
                        qty=order_qty,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY,
                        order_trade_session_type=TSType.RTH
                    )
                    # Record entry price for SL/TP logic
                    self.entry_price = buy_price