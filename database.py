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
        sql_create_portfolio_table = """ CREATE TABLE IF NOT EXISTS portfolio (
                                            id integer PRIMARY KEY,
                                            symbol text NOT NULL,
                                            quantity real NOT NULL,
                                            buy_price real NOT NULL,
                                            commission real NOT NULL, 
                                            buy_date text NOT NULL
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
    cur.execute("SELECT * FROM portfolio")
    rows = cur.fetchall()
    
    portfolio_list = []
    for row in rows:
        portfolio_list.append({
            "id": row[0],
            "السهم": row[1],
            "الكمية": row[2],
            "سعر الشراء": row[3],
            "العمولة": row[4],
            "تاريخ الشراء": row[5]
        })
    return portfolio_list
