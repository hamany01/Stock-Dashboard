import sqlite3

def create_connection():
    """إنشاء اتصال بقاعدة البيانات وإرجاع الاتصال."""
    conn = None
    try:
        conn = sqlite3.connect('portfolio.db') # سيتم إنشاء الملف تلقائيًا
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """إنشاء جدول المحفظة إذا لم يكن موجودًا."""
    try:
        sql_create_portfolio_table = """ CREATE TABLE IF NOT EXISTS portfolio (
                                            id integer PRIMARY KEY,
                                            symbol text NOT NULL,
                                            quantity real NOT NULL,
                                            buy_price real NOT NULL,
                                            buy_date text NOT NULL
                                        ); """
        c = conn.cursor()
        c.execute(sql_create_portfolio_table)
    except sqlite3.Error as e:
        print(e)

def add_transaction(conn, transaction):
    """إضافة معاملة شراء جديدة إلى المحفظة."""
    sql = ''' INSERT INTO portfolio(symbol,quantity,buy_price,buy_date)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, transaction)
    conn.commit()
    return cur.lastrowid

def get_portfolio(conn):
    """استرجاع كل الأسهم من المحفظة."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM portfolio")
    rows = cur.fetchall()
    # تحويل النتائج إلى قائمة من القواميس لسهولة التعامل
    portfolio_list = []
    for row in rows:
        portfolio_list.append({
            "id": row[0],
            "السهم": row[1],
            "الكمية": row[2],
            "سعر الشراء": row[3],
            "تاريخ الشراء": row[4]
        })
    return portfolio_list

# عند تشغيل هذا الملف لأول مرة، سيقوم بإنشاء قاعدة البيانات والجدول
if __name__ == '__main__':
    conn = create_connection()
    if conn is not None:
        create_table(conn)
        conn.close()
        print("تم إنشاء قاعدة البيانات والجدول بنجاح.")
