import streamlit as st
import configparser
import yfinance as yf
import pandas as pd
import ta
import database as db
import investpy
from datetime import date, timedelta
from gnews import GNews
import requests

# --- إعدادات الصفحة والاتصال بقاعدة البيانات ---
st.set_page_config(page_title="مدير المحفظة الذكي", layout="wide")
st.title("📊 مدير المحفظة الذكي للسوق السعودي")
conn = db.create_connection()
if conn:
    db.create_table(conn)

# --- الدوال التحليلية والذكاء الاصطناعي ---
API_URL = "https://api-inference.huggingface.co/models/CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment"

@st.cache_data(ttl="10m")
def get_stock_data(symbol):
    """يجلب بيانات السهم من yfinance، وإذا فشل، يجرب investpy."""
    try:
        data = yf.download(symbol, period="1y", progress=False, auto_adjust=True)
        if data.empty: raise ValueError("yfinance did not return data")
    except Exception:
        try:
            st.warning(f"المصدر الأول فشل لسهم {symbol}، جاري محاولة المصدر الاحتياطي...")
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            search_result = investpy.search_quotes(text=symbol.split('.')[0], products=['stocks'], countries=['saudi arabia'], n_results=1)
            data = search_result.retrieve_historical_data(from_date=start_date.strftime('%d/%m/%Y'), to_date=end_date.strftime('%d/%m/%Y'))
            if data.empty: return None, f"فشل المصدران"
        except Exception as e_investpy: return None, f"فشل المصدران: {e_investpy}"
            
    try:
        close_prices = pd.Series(data['Close'].values)
        data['RSI'] = ta.momentum.RSIIndicator(close=close_prices).rsi()
        macd = ta.trend.MACD(close=close_prices)
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        return data, None
    except Exception as e_ta: return None, f"فشل التحليل الفني: {e_ta}"

@st.cache_data(ttl="1h")
def analyze_news_sentiment(stock_name):
    """جلب وتحليل مشاعر الأخبار باستخدام API."""
    try:
        if 'HF_TOKEN' not in st.secrets:
            return "مفتاح Hugging Face غير موجود في الأسرار (Secrets)", []
        
        headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}
        
        google_news = GNews(language='ar', country='SA', max_results=5)
        news = google_news.get_news(stock_name)
        
        if not news:
            return "لا توجد أخبار حديثة", []
        
        titles = [article['title'] for article in news]
        
        response = requests.post(API_URL, headers=headers, json={"inputs": titles})
        results = response.json()

        if isinstance(results, dict) and 'error' in results:
             return f"خطأ من الـ API: {results['error']}", []

        sentiment_scores = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0}
        analyzed_articles = []

        for i, result_list in enumerate(results):
            best_result = max(result_list, key=lambda x: x['score'])
            label = best_result['label']
            sentiment_scores[label] += 1
            analyzed_articles.append({'title': titles[i], 'sentiment': label})

        if sentiment_scores['POSITIVE'] > sentiment_scores['NEGATIVE']:
            overall_sentiment = "إيجابي 👍"
        elif sentiment_scores['NEGATIVE'] > sentiment_scores['POSITIVE']:
            overall_sentiment = "سلبي 👎"
        else:
            overall_sentiment = "محايد 😐"
            
        return overall_sentiment, analyzed_articles
    except Exception as e:
        return f"خطأ في تحليل الأخبار: {e}", []

# --- تصميم الواجهة ---
tab1, tab2, tab3 = st.tabs(["محفظتي", "نظرة على السوق", "فرص استثمارية (AI)"])
# (الكود الخاص بالتبويب الأول والثاني يبقى كما هو)
with tab1:
    st.header("محفظتي الاستثمارية")
    # ...
with tab2:
    st.header("نظرة شاملة على السوق")
    # ...

# --- التبويب الثالث: فرص استثمارية (AI) ---
with tab3:
    st.header("🔬 تحليل مشاعر الأخبار بالذكاء الاصطناعي")
    st.markdown("اختر سهمًا من القائمة ليقوم الذكاء الاصطناعي بالبحث عن آخر الأخبار المتعلقة به وتحليل مشاعرها.")

    config = configparser.ConfigParser()
    config.read('config.ini')
    stocks_dict = dict(config['TadawulStocks'].items())
    display_list = [f"{symbol} - {name}" for symbol, name in stocks_dict.items()]

    selected_stock_display = st.selectbox("اختر السهم للتحليل:", display_list, key="ai_stock_selector")

    if st.button("تحليل مشاعر الأخبار الآن", key="ai_analyze_button"):
        stock_symbol = selected_stock_display.split(' - ')[0]
        stock_name = stocks_dict[stock_symbol]

        with st.spinner(f"⏳ جاري البحث عن أخبار '{stock_name}' وتحليلها عبر الـ API..."):
            overall_sentiment, articles = analyze_news_sentiment(stock_name)
        
        st.subheader(f"نتيجة تحليل المشاعر لسهم: {stock_name}")
        st.metric("الشعور العام للأخبار", str(overall_sentiment))

        with st.expander("عرض تفاصيل الأخبار التي تم تحليلها"):
            if articles:
                for article in articles:
                    sentiment_emoji = "👍" if article['sentiment'] == 'POSITIVE' else '👎' if article['sentiment'] == 'NEGATIVE' else '😐'
                    st.markdown(f"- {article['title']} **({sentiment_emoji})**")
            else:
                st.write("لم يتم العثور على مقالات لتحليلها.")
