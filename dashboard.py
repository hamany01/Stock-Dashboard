import streamlit as st
import configparser
import yfinance as yf
import pandas as pd
import ta
import database as db
from datetime import date

st.set_page_config(page_title="مدير المحفظة الذكي", layout="wide")
st.title("📊 مدير المحفظة الذكي للسوق السعودي")

# --- إعداد قاعدة البيانات ---
conn = db.create_connection()
if conn is not None:
    db.create_table(conn)

# --- تعريف الوظائف التحليلية ---
@st.cache_data(ttl="10m")
def get_stock_data(symbol):
    """يجلب بيانات السهم ويحسب المؤشرات."""
    try:
        data = yf.download(symbol, period="1y", progress=False, auto_adjust=True)
        if data.empty:
            return None, f"لم يتم العثور على بيانات للسهم {symbol}"
        
        close_prices = pd.Series(data['Close'].values)
        data['RSI'] = ta.momentum.RSIIndicator(close=close_prices).rsi()
        macd = ta.trend.MACD(close=close_prices)
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        
        return data, None
    except Exception as e:
        return None, str(e)

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
        # (الكود لعرض المحفظة يبقى كما هو)
        total_investment = 0.0
        current_value = 0.0
        error_messages = []

        for stock in portfolio_data:
            stock_data_live, error = get_stock_data(stock['السهم'])
            if error:
                error_messages.append(f"⚠️ فشل تحديث سعر سهم **{stock['السهم']}**. السبب: {error}")
                stock['السعر الحالي'] = "خطأ"
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


    # --- نموذج الإضافة المصحح ---
    with st.expander("➕ إضافة عملية شراء جديدة"):
        config = configparser.ConfigParser()
        config.read('config.ini')
        stocks_dict = dict(config['TadawulStocks'].items())
        display_list = [f"{symbol} - {name}" for symbol, name in stocks_dict.items()]
        
        # استخدام st.form يحل المشكلتين
        with st.form("new_transaction_form", clear_on_submit=True):
            st.write("أدخل تفاصيل الصفقة الجديدة:")
            
            t_symbol_display = st.selectbox("اختر السهم", display_list)
            t_quantity = st.number_input("أدخل الكمية", min_value=0.1, step=0.1)
            t_buy_price = st.number_input("أدخل سعر الشراء", min_value=0.01, step=0.01, format="%.2f")
            t_commission = st.number_input("أدخل عمولة الشراء", min_value=0.0, step=0.01)
            
            # زر الإضافة يكون دائمًا آخر عنصر داخل الـ form
            submitted = st.form_submit_button("إضافة الصفقة")

            if submitted:
                symbol_to_add = t_symbol_display.split(' - ')[0]
                transaction = (symbol_to_add, t_quantity, t_buy_price, t_commission, date.today().strftime("%Y-%m-%d"))
                db.add_transaction(conn, transaction)
                st.success(f"تمت إضافة {t_quantity} سهم من {symbol_to_add} إلى محفظتك.")
                st.cache_data.clear() # مسح الكاش مهم بعد كل إضافة
                st.rerun()


# --- التبويب الثاني: نظرة على السوق ---
with tab2:
    # الكود الخاص بهذا التبويب يبقى كما هو
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
            if stock_data_market is not None:
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

    df_market = pd.DataFrame(market_results)
    if not df_market.empty:
        st.dataframe(df_market.set_index('السهم'), use_container_width=True)
    else:
        st.warning("لم يتم العثور على بيانات لأي سهم.")


# --- التبويب الثالث: فرص استثمارية (AI) ---
with tab3:
    st.header("قيد التطوير: توصيات مدعومة بالذكاء الاصطناعي")
