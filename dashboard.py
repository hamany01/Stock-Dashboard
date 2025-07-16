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

# --- تصميم الواجهة ---
tab1, tab2, tab3 = st.tabs(["محفظتي", "نظرة على السوق", "فرص استثمارية (AI)"])

# --- التبويب الأول: محفظتي ---
with tab1:
    st.header("محفظتي الاستثمارية")
    
    if st.button("🔄 تحديث الأسعار التلقائي"):
        st.cache_data.clear()
        st.rerun()

    portfolio_data = db.get_portfolio(conn)

    if not portfolio_data:
        st.info("محفظتك فارغة. قم بإضافة أول عملية شراء.")
    else:
        # تحويل البيانات إلى DataFrame لتسهيل التعديل
        df_portfolio = pd.DataFrame(portfolio_data)

        # حساب القيم الحالية والأرباح
        for i, row in df_portfolio.iterrows():
            # استخدم السعر اليدوي إن وجد، وإلا حاول جلبه تلقائيًا
            if pd.notna(row['السعر اليدوي']):
                current_price = row['السعر اليدوي']
                df_portfolio.loc[i, 'مصدر السعر'] = "يدوي"
            else:
                stock_data_live, error = get_stock_data(row['السهم'])
                if error:
                    current_price = 0
                    df_portfolio.loc[i, 'مصدر السعر'] = "خطأ"
                else:
                    current_price = stock_data_live['Close'].iloc[-1]
                    df_portfolio.loc[i, 'مصدر السعر'] = "تلقائي"

            # حساب الأرباح
            if current_price > 0:
                buy_cost = (row['الكمية'] * row['سعر الشراء']) + row['العمولة']
                current_value = row['الكمية'] * current_price
                profit_loss = current_value - buy_cost
                df_portfolio.loc[i, 'السعر الحالي'] = f"{current_price:.2f}"
                df_portfolio.loc[i, 'الربح/الخسارة'] = f"{profit_loss:.2f}"
            else:
                df_portfolio.loc[i, 'السعر الحالي'] = "N/A"
                df_portfolio.loc[i, 'الربح/الخسارة'] = "N/A"
        
        # عرض ملخص المحفظة
        st.metric("القيمة الإجمالية للمحفظة", f"{df_portfolio.apply(lambda x: x['الكمية'] * float(x['السعر الحالي']) if x['السعر الحالي'] != 'N/A' else 0, axis=1).sum():.2f} ريال")

        # إضافة أعمدة التعديل
        df_portfolio['تعديل السعر'] = [False] * len(df_portfolio)
        edited_df = st.data_editor(df_portfolio, 
                                   column_config={"تعديل السعر": st.column_config.CheckboxColumn(required=True)},
                                   disabled=['السهم', 'الكمية', 'سعر الشراء', 'العمولة', 'تاريخ الشراء', 'الربح/الخسارة'],
                                   hide_index=True)
        
        # التحقق من أي سهم تم تحديد خانة "تعديل السعر" له
        edited_row = edited_df[edited_df['تعديل السعر']].iloc[0] if not edited_df[edited_df['تعديل السعر']].empty else None

        if edited_row is not None:
            with st.form(f"edit_form_{edited_row['id']}"):
                st.write(f"أدخل السعر الحالي الجديد لسهم **{edited_row['السهم']}**:")
                new_price = st.number_input("السعر الجديد", min_value=0.01, format="%.2f")
                submitted = st.form_submit_button("حفظ السعر")

                if submitted:
                    db.update_manual_price(conn, (new_price, edited_row['id']))
                    st.success("تم تحديث السعر بنجاح.")
                    st.rerun()

    # --- نموذج الإضافة ---
    with st.expander("➕ إضافة عملية شراء جديدة"):
        # ... الكود كما هو ...
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

# --- بقية التبويبات تبقى كما هي ---
with tab2:
    st.header("قيد التطوير: نظرة شاملة على السوق")
with tab3:
    st.header("قيد التطوير: توصيات مدعومة بالذكاء الاصطناعي")
