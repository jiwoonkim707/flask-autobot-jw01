from binance.client import Client
from datetime import datetime
import json
import os
from utils import send_telegram

class TradeEngine:
    def __init__(self, client, telegram_token, telegram_chat_id, filename="positions.json"):
        self.client = client
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.positions = {}
        self.filename = filename
        self.load_positions()

    def load_positions(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.positions = json.load(f)

    def save_positions(self):
        with open(self.filename, "w") as f:
            json.dump(self.positions, f, indent=4)

    def can_enter(self, symbol):
        return symbol not in self.positions

    def enter_position(self, symbol, direction, quantity):
        side = "BUY" if direction == "LONG" else "SELL"
        position_side = direction

        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                positionSide=position_side,
                type="MARKET",
                quantity=quantity
            )
        except Exception as e:
            send_telegram(f"❌ 진입 실패: {symbol} - {e}")
            return

        price = float(self.client.futures_symbol_ticker(symbol=symbol)['price'])
        entry_time = datetime.utcnow()

        self.positions[symbol] = {
            "side": direction,
            "entry_price": price,
            "quantity": quantity,
            "entry_time": str(entry_time),
            "stop_loss": price * 0.97 if direction == "LONG" else price * 1.03,
            "take_profit": price * 1.05 if direction == "LONG" else price * 0.95,
            "trailing_value": 0.02,
            "highest_price": price,
            "lowest_price": price,
            "timeout_minutes": 60
        }

        self.save_positions()
        send_telegram(f"✅ {direction} 진입 완료: {symbol}, 수량: {quantity}, 진입가: {price}")

    def close_position(self, symbol, reason, price):
        pos = self.positions[symbol]
        side = "SELL" if pos["side"] == "LONG" else "BUY"
        position_side = pos["side"]
        quantity = pos["quantity"]

        try:
            self.client.futures_create_order(
                symbol=symbol,
                side=side,
                positionSide=position_side,
                type="MARKET",
                quantity=quantity,
                reduceOnly=True
            )
        except Exception as e:
            send_telegram(f"❌ 청산 실패: {symbol} - {e}")
            return

        send_telegram(f"🔚 {reason} 청산: {symbol}, 가격: {price}")
        del self.positions[symbol]
        self.save_positions()

    def monitor_positions(self):
        now = datetime.utcnow()
        for symbol in list(self.positions):
            pos = self.positions[symbol]
            try:
                price = float(self.client.futures_symbol_ticker(symbol=symbol)['price'])
            except:
                continue

            if pos["side"] == "LONG":
                pos["highest_price"] = max(pos["highest_price"], price)
                trail_stop = pos["highest_price"] * (1 - pos["trailing_value"])
                if price <= trail_stop:
                    self.close_position(symbol, "트레일링 스탑", price)
                    continue
                if price <= pos["stop_loss"]:
                    self.close_position(symbol, "손절", price)
                    continue
                if price >= pos["take_profit"]:
                    self.close_position(symbol, "익절", price)
                    continue
            else:
                pos["lowest_price"] = min(pos["lowest_price"], price)
                trail_stop = pos["lowest_price"] * (1 + pos["trailing_value"])
                if price >= trail_stop:
                    self.close_position(symbol, "트레일링 스탑", price)
                    continue
                if price >= pos["stop_loss"]:
                    self.close_position(symbol, "손절", price)
                    continue
                if price <= pos["take_profit"]:
                    self.close_position(symbol, "익절", price)
                    continue

            entry_time = datetime.strptime(pos["entry_time"], "%Y-%m-%d %H:%M:%S.%f")
            if (now - entry_time).total_seconds() > pos["timeout_minutes"] * 60:
                self.close_position(symbol, "시간 초과", price)
