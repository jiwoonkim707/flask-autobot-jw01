import requests

def send_telegram(message, token=None, chat_id=None):
    # 기본값 설정 (환경변수나 고정값 등으로 대체 가능)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")
