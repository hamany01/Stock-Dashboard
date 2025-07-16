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
@st.cache_data(ttl="10m") # تخزين البيانات مؤقتًا لمدة 10 دقائق
def get_current_price(symbol):
    """
    يجلب آخر سعر إغلاق لسهم معين.
    يعيد قيمة float واحدة أو None في حالة الفشل.
    """
    try:
        # جلب بيانات آخر يومين لضمان الحصول على قيمة
        data = yf.download(symbol, period="2d", progress=False, auto_adjust=True)
        if not data.empty:
            # إرجاع آخر سعر كرقم float عادي
            return float(data['Close'].iloc[-1])
        return None
    except Exception:
        return None

# --- تصميم الواجهة باستخدام علامات التبويب ---
tab1, tab2, tab3 = st.tabs(["محفظتي", "نظرة على السوق", "فرص استثمارية (AI)"])

# --- التبويب الأول: محفظتي ---
with tab1:
    st.header("محفظتي الاستثمارية")

    portfolio_data = db.get_portfolio(conn)

    if not portfolio_data:
        st.info("محفظتك فارغة. قم بإضافة أول عملية شراء.")
    else:
        total_investment = 0.0
        current_value = 0.0

        for stock in portfolio_data:
            current_price = get_current_price(stock['السهم'])
            
            # --- هذا هو الشرط المصحح ---
            if current_price is not None:
                stock['السعر الحالي'] = f"{current_price:.2f}"
                buy_cost = stock['الكمية'] * stock['سعر الشراء']
                current_stock_value = stock['الكمية'] * current_price
                profit_loss = current_stock_value - buy_cost
                profit_loss_percent = (profit_loss / buy_cost) * 100 if buy_cost != 0 else 0
                stock['الربح/الخسارة'] = f"{profit_loss:.2f}"
                stock['نسبة التغيير %'] = f"{profit_loss_percent:.2f}"
                total_investment += buy_cost
                current_value += current_stock_value
            else:
                stock['السعر الحالي'] = "N/A"
                stock['الربح/الخسارة'] = "N/A"
                stock['نسبة التغيير %'] = "N/A"

        # عرض ملخص المحفظة
        if total_investment > 0:
            total_profit_loss = current_value - total_investment
            st.metric("القيمة الحالية للمحفظة", f"{current_value:.2f} ريال", f"{total_profit_loss:.2f} ريال")

        # عرض جدول المحفظة
        df_portfolio = pd.DataFrame(portfolio_data)
        display_cols = ['السهم', 'الكمية', 'سعر الشراء', 'السعر الحالي', 'الربح/الخسارة', 'نسبة التغيير %']
        st.dataframe(df_portfolio[display_cols].set_index('السهم'), use_container_width=True)

    # نموذج لإضافة معاملة جديدة
    with st.expander("➕ إضافة عملية شراء جديدة"):
        with st.form("new_transaction_form", clear_on_submit=True):
            config = configparser.ConfigParser()
            config.read('config.ini')
            symbols_list = config['Tadawul']['symbols'].split()

            t_symbol = st.selectbox("اختر السهم", symbols_list)
            t_quantity = st.number_input("أدخل الكمية", min_value=0.1, step=0.1)
            t_buy_price = st.number_input("أدخل سعر الشراء", min_value=0.01, step=0.01)
            submitted = st.form_submit_button("إضافة")

            if submitted:
                transaction = (t_symbol, t_quantity, t_buy_price, date.today().strftime("%Y-%m-%d"))
                db.add_transaction(conn, transaction)
                st.success(f"تمت إضافة {t_quantity} سهم من {t_symbol} إلى محفظتك.")
                st.rerun()

# أماكن مخصصة للتبويبات الأخرى
with tab2:
    st.header("قيد التطوير: نظرة شاملة على السوق")

with tab3:
    st.header("قيد التطوير: توصيات مدعومة بالذكاء الاصطناعي")
