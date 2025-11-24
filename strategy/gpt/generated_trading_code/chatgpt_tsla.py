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
        # FIXED POSITION SIZE
        self.qty = show_variable(2000, GlobalType.INT)

        # Trend indicators
        self.sma_fast_period = show_variable(50, GlobalType.INT)
        self.sma_slow_period = show_variable(200, GlobalType.INT)

        # RSI for mild pullback
        self.rsi_period = show_variable(14, GlobalType.INT)
        self.rsi_trigger_level = show_variable(40.0, GlobalType.FLOAT)

        # Risk management
        self.stop_loss_pct = show_variable(0.09, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.22, GlobalType.FLOAT)

        # Internal state
        self.entry_price = 0.0

    def handle_data(self):
        symbol = self.target_symbol
        curr_pos_qty = position_holding_qty(symbol=symbol)
        curr_price = current_price(symbol=symbol, price_type=THType.ALL)

        if curr_price is None:
            return

        # ---------------------------------------------------------
        # TREND INDICATORS (t-1)
        # ---------------------------------------------------------
        sma_fast = ma(
            symbol=symbol,
            period=self.sma_fast_period,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        sma_slow = ma(
            symbol=symbol,
            period=self.sma_slow_period,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        close_prev1 = ma(
            symbol=symbol,
            period=1,
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,
            session_type=THType.RTH
        )

        # ---------------------------------------------------------
        # RSI VALUES (t-1 and t-2)
        # ---------------------------------------------------------
        rsi_prev1 = rsi(
            symbol=symbol,
            period=self.rsi_period,
            bar_type=BarType.D1,
            select=2
        )

        rsi_prev2 = rsi(
            symbol=symbol,
            period=self.rsi_period,
            bar_type=BarType.D1,
            select=3
        )

        if close_prev1 is None or sma_fast is None or sma_slow is None:
            return

        # ---------------------------------------------------------
        # EXIT LOGIC FIRST
        # ---------------------------------------------------------
        if curr_pos_qty > 0:
            # 1) RSI cross down from above trigger
            bearish_rsi_cross = False
            if rsi_prev1 is not None and rsi_prev2 is not None:
                if rsi_prev2 > self.rsi_trigger_level and rsi_prev1 <= self.rsi_trigger_level:
                    bearish_rsi_cross = True

            # 2) Trend break: below SMA50
            trend_break = close_prev1 < sma_fast

            # 3) Stop loss / take profit
            hit_stop = False
            hit_tp = False

            if self.entry_price > 0:
                stop_price = self.entry_price * (1 - self.stop_loss_pct)
                tp_price = self.entry_price * (1 + self.take_profit_pct)

                if curr_price <= stop_price:
                    hit_stop = True
                if curr_price >= tp_price:
                    hit_tp = True

            should_exit = bearish_rsi_cross or trend_break or hit_stop or hit_tp

            if should_exit:
                sell_price = bid(symbol=symbol, level=5)
                if sell_price is None:
                    sell_price = curr_price

                place_limit(
                    symbol=symbol,
                    price=sell_price,
                    qty=curr_pos_qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    order_trade_session_type=TSType.RTH
                )
                self.entry_price = 0.0
                return

        # ---------------------------------------------------------
        # ENTRY LOGIC SECOND
        # Trend: Close > SMA50 > SMA200
        # Pullback rebound: RSI crosses UP above 40
        # ---------------------------------------------------------
        if curr_pos_qty <= 0:
            if rsi_prev1 is None or rsi_prev2 is None:
                return

            bullish_trend = (close_prev1 > sma_fast) and (sma_fast > sma_slow)

            bullish_rsi_cross = (
                rsi_prev2 < self.rsi_trigger_level and
                rsi_prev1 >= self.rsi_trigger_level
            )

            if bullish_trend and bullish_rsi_cross:
                buy_price = ask(symbol=symbol, level=5)
                if buy_price is None:
                    buy_price = curr_price

                max_can_buy = max_qty_to_buy_on_margin(
                    symbol=symbol,
                    price=buy_price,
                    order_type=OrdType.LMT
                )

                if max_can_buy is None or max_can_buy <= 0:
                    return

                trade_qty = min(self.qty, max_can_buy)
                trade_qty = int(trade_qty)

                if trade_qty <= 0:
                    return

                place_limit(
                    symbol=symbol,
                    price=buy_price,
                    qty=trade_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_trade_session_type=TSType.RTH
                )

                self.entry_price = buy_price