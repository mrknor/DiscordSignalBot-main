import pyodbc
from datetime import datetime
from secret import Secret

connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={Secret.server};DATABASE={Secret.database};UID={Secret.username};PWD={Secret.password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
def create_connection():
    return pyodbc.connect(connection_string)

def create_daily_table():
    table_name = get_table_name_for_today()
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')
            CREATE TABLE [{table_name}] (
                id INT PRIMARY KEY IDENTITY(1,1),
                symbol NVARCHAR(50) NOT NULL,
                signal_type NVARCHAR(10) NOT NULL,
                entry_point FLOAT NOT NULL,
                stop_loss FLOAT NOT NULL,
                invalidated_price FLOAT,
                take_profit FLOAT,
                sentiment FLOAT,
                is_open BIT DEFAULT 0,
                invalidated BIT DEFAULT 0,
                volume_confirmed BIT DEFAULT 0,
                total_profit FLOAT,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE()
            );
        ''')
        conn.commit()


def save_signal(symbol, signal_type, entry_point, stop_loss, invalidated_price, sentiment, volume_confirmed, take_profit=None):
    table_name = get_table_name_for_today()
    create_daily_table()  # Ensure the table exists
    
    # Calculate the profit target (PT), which is 3 times the risk
    risk = abs(entry_point - stop_loss)
    take_profit = entry_point + 3 * risk if signal_type == 'LONG' else entry_point - 3 * risk
    
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO [{table_name}] (symbol, signal_type, entry_point, stop_loss, invalidated_price, take_profit, sentiment, volume_confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, signal_type, entry_point, stop_loss, invalidated_price, take_profit, sentiment, volume_confirmed))
        conn.commit()


def update_signal(signal_id, total_profit, is_open, invalidated):
    table_name = get_table_name_for_today()
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE [{table_name}]
            SET total_profit = ?, is_open = ?, invalidated = ?, updated_at = GETDATE()
            WHERE id = ?
        ''', (total_profit, is_open, invalidated, signal_id))
        conn.commit()

def fetch_signals():
    table_name = get_table_name_for_today()
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM [{table_name}]')
        return cursor.fetchall()

def get_table_name_for_today():
    today = datetime.now().strftime('%m_%d_%Y')
    return f'dbo.{today}_intraday'

def fetch_open_signals():
    table_name = get_table_name_for_today()
    create_daily_table() 
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM [{table_name}] WHERE invalidated = 0')
        return cursor.fetchall()

def fetch_latest_price(symbol):
    # Implement your logic to fetch the latest price for the given symbol
    # This function should return the latest price as a float
    pass

def get_table_name_for_today():
    today = datetime.now().strftime('%m_%d_%Y')
    return f'{today}_intraday'

def update_signal_stop_loss(signal_id, new_stop_loss):
    table_name = get_table_name_for_today()
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE [{table_name}]
            SET stop_loss = ?, updated_at = GETDATE()
            WHERE id = ?
        ''', (new_stop_loss, signal_id))
        conn.commit()

def save_message(message):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signal_messages (message)
            VALUES (?)
        ''', (message,))
        conn.commit()

