import os

import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from plyer import notification
CONFIG = {
    "data_folder": r"C:\AmiBackup\Export",
    "telegram_token": "8742080021:AAGrTbH13Y5qSRXuByo4WYFk7C5HBxPMFl4",
    "telegram_chat_id": "969628143",
    "email_sender": "your_email@gmail.com",
    "email_password": "your_app_password_here",
    "email_receiver": "your_email@gmail.com",
    "watchlist": ["VNM", "FPT", "HPG", "GEX"],
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "volume_spike": 1.5,
}

def load_stock_data(symbol):
    filepath = os.path.join(CONFIG["data_folder"], f"{symbol}.csv")
    if not os.path.exists(filepath):
        print(f"[!] Không tìm thấy file: {filepath}")
        return None
    df = pd.read_csv(filepath, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df.columns = [c.strip().title() for c in df.columns]
    return df

def calculate_indicators(df):
    result = {}
    rsi = ta.rsi(df["Close"], length=14)
    result["rsi"] = round(float(rsi.iloc[-1]), 2)
    macd_df = ta.macd(df["Close"])
    result["macd"] = round(float(macd_df["MACD_12_26_9"].iloc[-1]), 2)
    result["macd_signal"] = round(float(macd_df["MACDs_12_26_9"].iloc[-1]), 2)
    result["macd_cross"] = "UP" if result["macd"] > result["macd_signal"] else "DOWN"
    result["ma20"] = round(float(ta.sma(df["Close"], length=20).iloc[-1]), 0)
    result["ma50"] = round(float(ta.sma(df["Close"], length=50).iloc[-1]), 0)
    bb = ta.bbands(df["Close"], length=20)
    bb.columns = [str(c) for c in bb.columns]
    bb_upper_col = [c for c in bb.columns if "BBU" in c][0]
    bb_lower_col = [c for c in bb.columns if "BBL" in c][0]
    result["bb_upper"] = round(float(bb[bb_upper_col].iloc[-1]), 0)
    result["bb_lower"] = round(float(bb[bb_lower_col].iloc[-1]), 0)
    result["price"] = round(float(df["Close"].iloc[-1]), 0)
    result["volume"] = int(df["Volume"].iloc[-1])
    result["volume_avg20"] = round(float(df["Volume"].tail(20).mean()), 0)
    result["volume_ratio"] = round(result["volume"] / result["volume_avg20"], 2)
    prev_close = float(df["Close"].iloc[-2])
    result["change_pct"] = round((result["price"] - prev_close) / prev_close * 100, 2)
    return result

def generate_signal(symbol, ind):
    alerts = []
    score = 0
    if ind["rsi"] >= CONFIG["rsi_overbought"]:
        alerts.append(f"⚠️ RSI = {ind['rsi']} — QUÁ MUA")
        score -= 1
    elif ind["rsi"] <= CONFIG["rsi_oversold"]:
        alerts.append(f"✅ RSI = {ind['rsi']} — QUÁ BÁN (cơ hội mua)")
        score += 1
    if ind["macd_cross"] == "UP":
        alerts.append("✅ MACD cắt LÊN — Tín hiệu tăng")
        score += 1
    else:
        alerts.append("⚠️ MACD cắt XUỐNG — Tín hiệu giảm")
        score -= 1
    if ind["price"] > ind["ma20"] and ind["price"] > ind["ma50"]:
        score += 1
    elif ind["price"] < ind["ma20"] and ind["price"] < ind["ma50"]:
        alerts.append("⚠️ Giá dưới MA20 và MA50")
        score -= 1
    if ind["volume_ratio"] >= CONFIG["volume_spike"]:
        alerts.append(f"📊 Khối lượng đột biến: {ind['volume_ratio']}× TB20")
    if score >= 2:
        signal = "MUA 🟢"
    elif score <= -2:
        signal = "BÁN 🔴"
    else:
        signal = "GIỮ 🟡"
    return {"symbol": symbol, "signal": signal, "alerts": alerts,
            "indicators": ind, "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")}

def format_message(result):
    ind = result["indicators"]
    lines = [
        f"📈 CẢNH BÁO CỔ PHIẾU",
        f"━━━━━━━━━━━━━━━━━━━━━",
        f"🏷 Mã: {result['symbol']}   |   {result['timestamp']}",
        f"💰 Giá: {ind['price']:,.0f} VNĐ  ({'+' if ind['change_pct']>0 else ''}{ind['change_pct']}%)",
        f"🎯 Tín hiệu: {result['signal']}",
        f"━━━━━━━━━━━━━━━━━━━━━",
        f"RSI(14): {ind['rsi']}",
        f"MACD: {ind['macd']} | Signal: {ind['macd_signal']}",
        f"MA20: {ind['ma20']:,.0f} | MA50: {ind['ma50']:,.0f}",
        f"Bollinger: {ind['bb_lower']:,.0f} – {ind['bb_upper']:,.0f}",
        f"KL: {ind['volume']:,} ({ind['volume_ratio']}× TB20)",
    ]
    if result["alerts"]:
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔔 Cảnh báo:")
        for a in result["alerts"]:
            lines.append(f"   {a}")
    return "\n".join(lines)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CONFIG["telegram_chat_id"],
                          "text": message}, timeout=10)
        print("  [Telegram] Đã gửi ✓" if r.status_code == 200 else f"  [Telegram] Lỗi: {r.text}")
    except Exception as e:
        print(f"  [Telegram] Lỗi: {e}")

def send_email(subject, body):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = CONFIG["email_sender"]
    msg["To"] = CONFIG["email_receiver"]
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(CONFIG["email_sender"], CONFIG["email_password"])
            s.sendmail(CONFIG["email_sender"], CONFIG["email_receiver"], msg.as_string())
        print("  [Email] Đã gửi ✓")
    except Exception as e:
        print(f"  [Email] Lỗi: {e}")

def send_windows_notification(title, message):
    try:
        notification.notify(title=title, message=message, timeout=8)
        print("  [Windows] Thông báo ✓")
    except Exception as e:
        print(f"  [Windows] Lỗi: {e}")

def run_analysis():
    print(f"\n{'='*50}")
    print(f"  PHÂN TÍCH — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")
    for symbol in CONFIG["watchlist"]:
        print(f"\n[{symbol}] Đang phân tích...")
        df = load_stock_data(symbol)
        if df is None or len(df) < 60:
            print("  Bỏ qua (thiếu dữ liệu)")
            continue
        ind = calculate_indicators(df)
        result = generate_signal(symbol, ind)
        msg = format_message(result)
        if len(result["alerts"]) > 0 or result["signal"] != "GIỮ 🟡":
            print(f"  → {result['signal']} — Gửi cảnh báo...")
            send_telegram(msg)
            ind2 = result["indicators"]
            send_windows_notification(f"Cảnh báo: {symbol}",
                f"{result['signal']}\nGiá: {ind2['price']:,.0f} VNĐ | RSI: {ind2['rsi']}")
        else:
            print(f"  → {result['signal']} — Không có cảnh báo")
    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    run_analysis()