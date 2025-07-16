import sqlite3

def create_connection(db_file="portfolio.db"):
    """إنشاء اتصال بقاعدة بيانات SQLite (افتراضي: portfolio.db)."""
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """إنشاء جدول الصفقات إذا لم يكن موجودا."""
    sql = """
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        السهم TEXT NOT NULL,
        الكمية REAL NOT NULL,
        سعر الشراء REAL NOT NULL,
        العمولة REAL DEFAULT 0,
        تاريخ الشراء TEXT NOT NULL,
        السعر اليدوي REAL DEFAULT NULL
    )
    """
    try:
        c = conn.cursor()
        c.execute(sql)
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def add_transaction(conn, transaction):
    """إضافة صفقة جديدة للمحفظة."""
    sql = """
    INSERT INTO portfolio (السهم, الكمية, سعر الشراء, العمولة, تاريخ الشراء)
    VALUES (?, ?, ?, ?, ?)
    """
    try:
        c = conn.cursor()
        c.execute(sql, transaction)
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def get_portfolio(conn):
    """جلب جميع الصفقات من المحفظة كقائمة قواميس."""
    sql = "SELECT id, السهم, الكمية, سعر الشراء, العمولة, تاريخ الشراء, السعر اليدوي FROM portfolio"
    try:
        c = conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        cols = [column[0] for column in c.description]
        data = [dict(zip(cols, row)) for row in rows]
        return data
    except sqlite3.Error as e:
        print(e)
        return []

def update_manual_price(conn, data):
    """تحديث السعر اليدوي لسهم معين."""
    sql = "UPDATE portfolio SET السعر اليدوي = ? WHERE id = ?"
    try:
        c = conn.cursor()
        c.execute(sql, data)
        conn.commit()
    except sqlite3.Error as e:
        print(e)
