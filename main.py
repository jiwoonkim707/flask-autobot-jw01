from flask import Flask, request
from binance.client import Client
import threading
from trade_engine import TradeEngine
from monitor import Monitor
from utils import send_telegram

# === 사용자 설정 ===
BINANCE_API_KEY = "cxUKq5IxpkmxRsAYkV7gn3jMVrxMVsexN0dolzWEV3cFagb0U1QDODUMD1dMNzXu"
BINANCE_API_SECRET = "uKajWGx5tqjnWmGk4RfZsqAejhvn3sMI6NI6BcR5msLzK8l649hwdnnBZlilj91V"
TELEGRAM_TOKEN = "8000978154:AAHYqhD3E7AKQsxR1F1ss3m8kgssY79ZSEQ"
TELEGRAM_CHAT_ID = "7752744045"
WEBHOOK_SECRET_KEY = "mysecret"
INVEST_RATIO = 0.7  # 총 잔고의 70%를 투자 한도로 설정

# === 초기화 ===
app = Flask(__name__)
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
engine = TradeEngine(client, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
monitor = Monitor(client, engine)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("secret") != WEBHOOK_SECRET_KEY:
        return "unauthorized", 403

    symbol = data.get("symbol", "BTCUSDT")
    action = data.get("action", "buy").lower()
    quantity = data.get("quantity")  # optional, if fixed quantity sent from TradingView

    # 현재 총 USDT 잔고 가져오기
    balance = client.futures_account_balance()
    usdt_balance = next((float(asset['balance']) for asset in balance if asset['asset'] == 'USDT'), 0)
    usdt_amount = round(usdt_balance * INVEST_RATIO * 0.2, 2)  # 월 한도의 20%씩 진입

    amount = float(quantity) if quantity else usdt_amount

    if not engine.can_enter(symbol):
        return "already in position"

    if action == "buy":
        engine.enter_position(symbol, "LONG", amount)
        send_telegram(f"🚀 롱 진입: {symbol}, 금액: {amount} USDT")
        return "buy executed"

    elif action == "sell":
        engine.enter_position(symbol, "SHORT", amount)
        send_telegram(f"🔻 숏 진입: {symbol}, 금액: {amount} USDT")
        return "sell executed"

    return "invalid action", 400

if __name__ == "__main__":
    threading.Thread(target=monitor.start).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
