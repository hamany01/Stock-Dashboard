import sqlite3

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('portfolio.db')
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
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

def add_transaction(conn, transaction):
    sql = ''' INSERT INTO portfolio(symbol,quantity,buy_price,commission,buy_date)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, transaction)
    conn.commit()
    return cur.lastrowid

def get_portfolio(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, quantity, buy_price, commission, buy_date, manual_price FROM portfolio")
    rows = cur.fetchall()
    
    portfolio_list = []
    for row in rows:
        portfolio_list.append({
            "id": row[0],
            "السهم": row[1],
            "الكمية": row[2],
            "سعر الشراء": row[3],
            "العمولة": row[4],
            "تاريخ الشراء": row[5],
            "السعر اليدوي": row[6]
        })
    return portfolio_list

def update_manual_price(conn, price_data):
    """تحديث السعر اليدوي لسهم معين."""
    sql = ''' UPDATE portfolio
              SET manual_price = ?
              WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(sql, price_data)
    conn.commit()

def clear_manual_price(conn, stock_id):
    """مسح السعر اليدوي والعودة للسعر التلقائي."""
    sql = ''' UPDATE portfolio
              SET manual_price = NULL
              WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(sql, (stock_id,))
    conn.commit()
