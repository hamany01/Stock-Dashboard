import configparser
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import yfinance as yf
import pandas as pd
import ta

def load_config(filename='config.ini'):
    """يقرأ ملف الإعدادات."""
    config = configparser.ConfigParser()
    config.read(filename)
    return config

def analyze_stock(symbol):
    """يحلل السهم الواحد ويعيد التوصية كنص إذا كانت قوية."""
    try:
        data = yf.download(symbol, period="6mo", progress=False)
        if data.empty:
            return None

        # حساب المؤشرات
        data['RSI'] = ta.momentum.RSIIndicator(close=data['Close']).rsi()
        macd = ta.trend.MACD(close=data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()

        # أخذ آخر قراءة
        latest = data.iloc[-1]
        rsi = latest['RSI']
        macd_val = latest['MACD']
        macd_signal = latest['MACD_signal']

        # منطق التوصية
        if rsi < 35 and macd_val > macd_signal:
            rec = "🟢 إشارة شراء قوية محتملة"
        elif rsi > 65 and macd_val < macd_signal:
            rec = "🔴 إشارة بيع قوية محتملة"
        else:
            return None # لا توجد إشارة تستحق الذكر

        return f"--- {symbol} ---\n{rec}\nRSI: {rsi:.2f}\nMACD: {macd_val:.2f}\n"
    except Exception as e:
        print(f"حدث خطأ أثناء تحليل {symbol}: {e}")
        return None

def send_notifications(message_body, config):
    """يرسل الإشعارات عبر البريد والواتساب."""
    # إرسال البريد الإلكتروني
    try:
        email_cfg = config['Email']
        msg = MIMEText(message_body)
        msg["Subject"] = "تنبيهات الأسهم اليومية"
        msg["From"] = email_cfg['email_from']
        msg["To"] = email_cfg['email_to']
        with smtplib.SMTP(email_cfg['smtp_server'], int(email_cfg['smtp_port'])) as server:
            server.starttls()
            server.login(email_cfg['email_from'], email_cfg['email_password'])
            server.send_message(msg)
        print("✅ تم إرسال البريد الإلكتروني بنجاح.")
    except Exception as e:
        print(f"❌ فشل إرسال البريد الإلكتروني: {e}")

    # إرسال رسالة واتساب
    try:
        twilio_cfg = config['Twilio']
        # تأكد من أن SID والتوكن ليسا قيمًا افتراضية
        if twilio_cfg['account_sid'] != 'your_twilio_sid':
            client = Client(twilio_cfg['account_sid'], twilio_cfg['auth_token'])
            client.messages.create(body=message_body, from_=twilio_cfg['twilio_number'], to=twilio_cfg['your_whatsapp'])
            print("✅ تم إرسال رسالة واتساب بنجاح.")
    except Exception as e:
        print(f"❌ فشل إرسال رسالة واتساب: {e}")

def main():
    """النقطة الرئيسية لتشغيل البرنامج."""
    print("🚀 بدء تشغيل نظام تحليل الأسهم...")
    config = load_config()
    
    symbols = config['Tadawul']['symbols'].split()
    strong_signals = []
    
    print(f"🔍 جاري تحليل {len(symbols)} سهم...")
    for symbol in symbols:
        result = analyze_stock(symbol)
        if result:
            strong_signals.append(result)
    
    if strong_signals:
        message = "\n".join(strong_signals)
        print("\n🔔 تم العثور على توصيات هامة:\n")
        print(message)
        send_notifications(message, config)
    else:
        print("\n✅ لا توجد إشارات قوية اليوم.")

if __name__ == "__main__":
    main()
    input("\nاضغط على Enter للخروج...")
