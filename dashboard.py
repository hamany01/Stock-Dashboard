import streamlit as st
import configparser
import yfinance as yf
import pandas as pd
import ta
import database as db
import investpy
from datetime import date, timedelta

st.set_page_config(page_title="مدير المحفظة الذكي", layout="wide")
st.title("📊 مدير المحفظة الذكي للسوق السعودي")

# --- إعداد قاعدة البيانات ---
conn = db.create_connection()
if conn is not None:
    db.create_table(conn)

# --- تعريف الوظائف التحليلية ---
@st.cache_data(ttl="10m")
def get_stock_data(symbol):
    """
    يجلب بيانات السهم من yfinance، وإذا فشل، يجرب investpy كمصدر احتياطي.
    """
    try:
        # --- المصدر الأول: yfinance ---
        data = yf.download(symbol, period="1y", progress=False, auto_adjust=True)
        if data.empty:
            raise ValueError("yfinance did not return data")
    except Exception as e:
        try:
            # --- المصدر الثاني: investpy ---
            st.warning(f"المصدر الأول فشل لسهم {symbol}، جاري محاولة المصدر الاحتياطي...")
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            search_result = investpy.search_quotes(text=symbol.split('.')[0], products=['stocks'], countries=['saudi arabia'], n_results=1)
            data = search_result.retrieve_historical_data(from_date=start_date.strftime('%d/%m/%Y'), to_date=end_date.strftime('%d/%m/%Y'))
            if data.empty:
                return None, f"فشل المصدران لجلب بيانات {symbol}"
        except Exception as e_investpy:
            return None, f"فشل المصدران لجلب بيانات {symbol}: {e_investpy}"
            
    # --- حساب المؤشرات (مشترك بين المصدرين) ---
    try:
        close_prices = pd.Series(data['Close'].values)
        data['RSI'] = ta.momentum.RSIIndicator(close=close_prices).rsi()
        macd = ta.trend.MACD(close=close_prices)
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        return data, None
    except Exception as e_ta:
        return None, f"نجح جلب البيانات ولكن فشل التحليل الفني: {e_ta}"

# --- بقية الكود يبقى كما هو ---
# (الكود الخاص بالتبويبات والمحفظة)

# --- تصميم الواجهة باستخدام علامات التبويب ---
tab1, tab2, tab3 = st.tabs(["محفظتي", "نظرة على السوق", "فرص استثمارية (AI)"])

# --- التبويب الأول: محفظتي ---
with tab1:
    st.header("محفظتي الاستثمارية")
    
    if st.button("🔄 تحديث أسعار المحفظة"):
        st.cache_data.clear()
        st.rerun()

    portfolio_data = db.get_portfolio(conn)

    if not portfolio_data:
        st.info("محفظتك فارغة. قم بإضافة أول عملية شراء.")
    else:
        total_investment = 0.0
        current_value = 0.0
        error_messages = []

        for stock in portfolio_data:
            stock_data_live, error = get_stock_data(stock['السهم'])
            if error:
                error_messages.append(f"⚠️ فشل تحديث سعر سهم **{stock['السهم']}**.")
                stock['السعر الحالي'] = "خطأ"
                stock['الربح/الخسارة'] = "N/A"
            else:
                current_price = stock_data_live['Close'].iloc[-1]
                stock['السعر الحالي'] = f"{current_price:.2f}"
                buy_cost = (stock['الكمية'] * stock['سعر الشراء']) + stock['العمولة']
                current_stock_value = stock['الكمية'] * current_price
                profit_loss = current_stock_value - buy_cost
                stock['الربح/الخسارة'] = f"{profit_loss:.2f}"
                total_investment += buy_cost
                current_value += current_stock_value
        
        if error_messages:
            for msg in error_messages:
                st.warning(msg)

        if total_investment > 0:
            total_profit_loss = current_value - total_investment
            st.metric("القيمة الحالية للمحفظة", f"{current_value:.2f} ريال", f"{total_profit_loss:.2f} ريال (صافي)")

        df_portfolio = pd.DataFrame(portfolio_data)
        display_cols = ['السهم', 'الكمية', 'سعر الشراء', 'العمولة', 'السعر الحالي', 'الربح/الخسارة']
        st.dataframe(df_portfolio[display_cols].set_index('السهم'), use_container_width=True)

    with st.expander("➕ إضافة عملية شراء جديدة"):
        with st.form("new_transaction_form", clear_on_submit=True):
            config = configparser.ConfigParser()
            config.read('config.ini')
            stocks_dict = dict(config['TadawulStocks'].items())
            display_list = [f"{symbol} - {name}" for symbol, name in stocks_dict.items()]
            
            t_symbol_display = st.selectbox("اختر السهم", display_list)
            t_quantity = st.number_input("أدخل الكمية", min_value=0.1)
            t_buy_price = st.number_input("أدخل سعر الشراء", min_value=0.01, format="%.2f")
            t_commission = st.number_input("أدخل عمولة الشراء", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("إضافة الصفقة")

            if submitted:
                symbol_to_add = t_symbol_display.split(' - ')[0]
                transaction = (symbol_to_add, t_quantity, t_buy_price, t_commission, date.today().strftime("%Y-%m-%d"))
                db.add_transaction(conn, transaction)
                st.success(f"تمت إضافة {t_quantity} سهم من {symbol_to_add} إلى محفظتك.")
                st.cache_data.clear()
                st.rerun()

# --- التبويب الثاني: نظرة على السوق ---
with tab2:
    st.header("نظرة شاملة على السوق")
    config = configparser.ConfigParser()
    config.read('config.ini')
    stocks_dict_market = dict(config['TadawulStocks'].items())
    
    market_results = []
    if st.button("🔄 تحديث بيانات السوق", key="market_refresh"):
        st.cache_data.clear()
        st.rerun()
        
    with st.spinner("⏳ جاري تحليل السوق..."):
        for symbol, name in stocks_dict_market.items():
            stock_data_market, error = get_stock_data(symbol)
            if not error:
                latest_data = stock_data_market.iloc[-1]
                rsi = latest_data['RSI']
                macd_val = latest_data['MACD']
                macd_signal = latest_data['MACD_signal']
                recommendation = "⚪️ حيادي"
                if rsi < 35 and macd_val > macd_signal:
                    recommendation = "🟢 شراء محتمل"
                elif rsi > 65 and macd_val < macd_signal:
                    recommendation = "🔴 بيع محتمل"
                
                market_results.append({
                    "السهم": f"{symbol} - {name}",
                    "السعر الحالي": f"{latest_data['Close']:.2f}",
                    "RSI": f"{rsi:.2f}",
                    "التوصية": recommendation
                })

    if market_results:
        df_market = pd.DataFrame(market_results)
        st.dataframe(df_market.set_index('السهم'), use_container_width=True)
    else:
        st.warning("لم يتم العثور على بيانات لأي سهم في السوق حاليًا.")

# --- التبويب الثالث: فرص استثمارية (AI) ---
with tab3:
    st.header("قيد التطوير: توصيات مدعومة بالذكاء الاصطناعي")
