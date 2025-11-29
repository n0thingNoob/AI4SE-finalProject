# =========================================================
# Strategy: NVDA_Uptrend_DipBuy_SMA100_RSI45
# Archetype: Type C (Trend + Dip)
# - Buy only in uptrend (Price > SMA100) AND short-term dip (RSI < 45)
# - Exit on trend break (Price < SMA100) OR momentum rebound (RSI > 65)
# - Risk controls: Stop Loss 7%, Take Profit 18%
# =========================================================

class Strategy(StrategyBase):
    def custom_indicator(self):
        # Mandatory convention function required by Moomoo
        # Even if unused, it MUST exist inside the class.
        return None
    def initialize(self):
        declare_strategy_type(AlgoStrategyType.SECURITY)
        self.trigger_symbols()
        self.global_variables()

        # Internal state for risk management
        self.entry_price = None

    def trigger_symbols(self):
        # Allow user to select target in UI
        self.target_symbol = declare_trig_symbol()

    def global_variables(self):
        # Position sizing
        self.qty = show_variable(2000, GlobalType.INT)

        # Trend + Dip parameters
        self.sma_period = show_variable(100, GlobalType.INT)
        self.rsi_period = show_variable(14, GlobalType.INT)

        self.rsi_entry_th = show_variable(45, GlobalType.FLOAT)  # buy dip
        self.rsi_exit_th = show_variable(65, GlobalType.FLOAT)   # take rebound

        # Risk controls (percent as decimals)
        self.stop_loss_pct = show_variable(0.07, GlobalType.FLOAT)
        self.take_profit_pct = show_variable(0.18, GlobalType.FLOAT)

        # Execution controls
        self.slippage_pct = show_variable(0.001, GlobalType.FLOAT)  # 0.10% price buffer for limit orders

    def handle_data(self):
        # --------------------------
        # 1) Fetch Data First
        # --------------------------
        curr_price = current_price(symbol=self.target_symbol, price_type=THType.ALL)

        sma100 = ma(
            symbol=self.target_symbol,
            period=int(self.sma_period),
            bar_type=BarType.D1,
            data_type=DataType.CLOSE,
            select=2,                 # previous completed daily bar (no repaint)
            session_type=THType.RTH
        )

        rsi14 = rsi(
            symbol=self.target_symbol,
            period=int(self.rsi_period),
            bar_type=BarType.D1,
            select=2                  # previous completed daily bar (no repaint)
        )

        # Level 1/5 quotes for more aggressive execution
        ask_p = ask(symbol=self.target_symbol, level=5)
        bid_p = bid(symbol=self.target_symbol, level=5)

        # --------------------------
        # 2) Validation
        # --------------------------
        if curr_price is None or sma100 is None or rsi14 is None:
            return

        if ask_p is None or bid_p is None:
            return

        curr_qty = position_holding_qty(symbol=self.target_symbol)
        has_pos = (curr_qty is not None and curr_qty > 0)

        # --------------------------
        # Helper: compute PnL%
        # --------------------------
        def unrealized_pnl_pct(entry_p, now_p):
            if entry_p is None or entry_p <= 0:
                return None
            return (now_p - entry_p) / entry_p

        # --------------------------
        # 3) Exit Logic (Priority 1)
        # --------------------------
        if has_pos:
            # If we somehow lost entry_price (restart), fall back to current price as a safe placeholder
            # (This prevents divide-by-zero / None crashes; risk controls become inert until next entry.)
            if self.entry_price is None or self.entry_price <= 0:
                self.entry_price = curr_price

            pnl_pct = unrealized_pnl_pct(self.entry_price, curr_price)

            trend_break = (curr_price < sma100)
            momentum_rebound = (rsi14 > float(self.rsi_exit_th))

            stop_loss_hit = (pnl_pct is not None and pnl_pct <= -float(self.stop_loss_pct))
            take_profit_hit = (pnl_pct is not None and pnl_pct >= float(self.take_profit_pct))

            if trend_break or momentum_rebound or stop_loss_hit or take_profit_hit:
                # aggressive sell: start from bid(level=5), apply small price buffer
                sell_price = bid_p * (1.0 - float(self.slippage_pct))

                place_limit(
                    symbol=self.target_symbol,
                    price=sell_price,
                    qty=curr_qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    order_trade_session_type=TSType.RTH
                )

                # Clear entry tracking after exit attempt
                self.entry_price = None
                return

        # --------------------------
        # 4) Entry Logic (Priority 2)
        # --------------------------
        if not has_pos:
            uptrend = (curr_price > sma100)
            dip_signal = (rsi14 < float(self.rsi_entry_th))

            if uptrend and dip_signal:
                # Check max buy (margin) before placing order
                max_can_buy = max_qty_to_buy_on_margin(
                    symbol=self.target_symbol,
                    price=curr_price,
                    order_type=OrdType.LMT
                )

                if max_can_buy is None or max_can_buy <= 0:
                    return

                buy_qty = int(self.qty)
                if buy_qty <= 0:
                    return

                # Cap by broker limit
                if buy_qty > max_can_buy:
                    buy_qty = int(max_can_buy)

                if buy_qty <= 0:
                    return

                # aggressive buy: start from ask(level=5), apply small price buffer
                buy_price = ask_p * (1.0 + float(self.slippage_pct))

                place_limit(
                    symbol=self.target_symbol,
                    price=buy_price,
                    qty=buy_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_trade_session_type=TSType.RTH
                )

                # Track entry for SL/TP (best-effort: assume fill near our limit)
                self.entry_price = buy_price
                return