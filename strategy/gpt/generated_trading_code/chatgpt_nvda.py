class Strategy(StrategyBase):
    def custom_indicator(self):
        # Mandatory convention function required by Moomoo
        # Even if unused, it MUST exist inside the class.
        return None
        
    def initialize(self):
        # Declare strategy type and initialize configuration
        declare_strategy_type(AlgoStrategyType.SECURITY)
        self.trigger_symbols()
        self.global_variables()

        # Internal state: track last entry price for stop-loss / take-profit
        self.entry_price = None

    def trigger_symbols(self):
        # Allow user to select the trading symbol in the UI
        self.target_symbol = declare_trig_symbol()

    def global_variables(self):
        # Position size (fixed size, as per strategy description)
        self.qty = show_variable(2000, GlobalType.INT)

        # Indicator parameters (parameterized for UI)
        self.trend_ma_period = show_variable(50, GlobalType.INT)     # SMA(50) trend filter
        self.bb_ma_period = show_variable(20, GlobalType.INT)        # 20-period base for "Bollinger-like" pullback
        self.rsi_period = show_variable(14, GlobalType.INT)          # RSI(14)

        # RSI thresholds for pullback and overbought
        self.rsi_pullback_low = show_variable(30.0, GlobalType.FLOAT)   # >= 30
        self.rsi_pullback_high = show_variable(45.0, GlobalType.FLOAT)  # <= 45
        self.rsi_overbought = show_variable(70.0, GlobalType.FLOAT)     # >= 70

        # Approximate lower-band distance and buffer (proxy for LowerBB20_2 * 1.01)
        self.lower_band_width = show_variable(0.04, GlobalType.FLOAT)   # 4% below MA20 as a proxy for lower BB
        self.lower_band_buffer = show_variable(1.01, GlobalType.FLOAT)  # 1% buffer above that lower band

        # Stop loss / take profit (as fractions: 0.08 = 8%, 0.18 = 18%)
        self.stop_loss_pct = show_variable(0.08, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.18, GlobalType.FLOAT)

    def handle_data(self):
        # -----------------------------
        # 1. Fetch market data & indicators (all from previous completed bar)
        # -----------------------------
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)

        # Use MA(1) of previous bar close as Close[t-1]
        prev_close = ma(
            symbol=self.target_symbol,
            period=1,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        sma_trend = ma(
            symbol=self.target_symbol,
            period=self.trend_ma_period,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        ma_bb_base = ma(
            symbol=self.target_symbol,
            period=self.bb_ma_period,
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

        # Validate indicator values
        if (
            prev_close is None
            or sma_trend is None
            or ma_bb_base is None
            or rsi_val is None
        ):
            return

        # Estimate a "lower Bollinger band" using MA20 minus a configurable width
        # LowerBB_est ≈ MA20 * (1 - lower_band_width)
        lower_band_est = ma_bb_base * (1.0 - self.lower_band_width)
        pullback_threshold = lower_band_est * self.lower_band_buffer

        # Current position quantity
        curr_qty = position_holding_qty(symbol=self.target_symbol)

        # -----------------------------
        # 2. EXIT logic (process exits before new entries)
        # -----------------------------
        if curr_qty > 0 and self.entry_price is not None:
            stop_loss_price = self.entry_price * (1.0 - self.stop_loss_pct)
            take_profit_price = self.entry_price * (1.0 + self.take_profit_pct)

            exit_trend_break = prev_close < sma_trend
            exit_rsi_overbought = rsi_val >= self.rsi_overbought
            exit_take_profit = prev_close >= take_profit_price
            exit_stop_loss = prev_close <= stop_loss_price

            if (
                exit_trend_break
                or exit_rsi_overbought
                or exit_take_profit
                or exit_stop_loss
            ):
                # Aggressive sell: use bid level 5
                sell_price = bid(symbol=self.target_symbol, level=5)
                if sell_price is None:
                    sell_price = curr_price

                if sell_price is not None:
                    place_limit(
                        symbol=self.target_symbol,
                        price=sell_price,
                        qty=curr_qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY,
                        order_trade_session_type=TSType.RTH
                    )
                    # Reset entry_price once position is closed
                    self.entry_price = None

                # Avoid entering again in the same bar after exiting
                return

        # -----------------------------
        # 3. ENTRY logic (only if flat)
        # -----------------------------
        if curr_qty == 0:
            # (2) Close[t-1] > SMA50[t-1] — bullish medium-term trend filter
            in_bull_trend = prev_close > sma_trend

            # (3) Close[t-1] <= LowerBB20_2[t-1] * 1.01 (approximated)
            near_lower_band = prev_close <= pullback_threshold

            # (4) RSI14[t-1] between 30 and 45
            rsi_in_pullback_zone = (
                rsi_val >= self.rsi_pullback_low
                and rsi_val <= self.rsi_pullback_high
            )

            if in_bull_trend and near_lower_band and rsi_in_pullback_zone:
                # Aggressive buy: use ask level 5
                buy_price = ask(symbol=self.target_symbol, level=5)
                if buy_price is None:
                    buy_price = curr_price

                if buy_price is None:
                    return

                # Respect margin / max-buy constraint
                max_can_buy = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol,
                    price=buy_price,
                    order_type=OrdType.LMT
                )

                if max_can_buy is None or max_can_buy <= 0:
                    return

                trade_qty = self.qty
                if trade_qty > max_can_buy:
                    trade_qty = max_can_buy

                if trade_qty <= 0:
                    return

                place_limit(
                    symbol=self.target_symbol,
                    price=buy_price,
                    qty=trade_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_trade_session_type=TSType.RTH
                )

                # Store the executed entry price for SL/TP logic
                self.entry_price = buy_price