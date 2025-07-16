import sqlite3

def create_connection():
    """إنشاء اتصال بقاعدة البيانات وإرجاع الاتصال."""
    conn = None
    try:
        conn = sqlite3.connect('portfolio.db')
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """إنشاء جدول المحفظة إذا لم يكن موجودًا، مع إضافة حقل السعر اليدوي."""
    try:
        # إضافة حقل manual_price لتخزين السعر اليدوي
        sql_create_portfolio_table = """ CREATE TABLE IF NOT EXISTS portfolio (
                                            id integer PRIMARY KEY,
                                            symbol text NOT NULL,
                                            quantity real NOT NULL,
                                            buy_price real NOT NULL,
                                            commission real NOT NULL, 
                                            buy_date text NOT NULL,
                                            manual_price real DEFAULT NULL
                                        ); """
        c = conn.cursor()
        c.execute(sql_create_portfolio_table)
    except sqlite3.Error as e:
        print(e)

def add_transaction(
