
# USE [Stocks]
# GO

# /****** Object:  Table [dbo].[signals]    Script Date: 6/12/2024 5:20:16 PM ******/
# SET ANSI_NULLS ON
# GO

# SET QUOTED_IDENTIFIER ON
# GO

# CREATE TABLE [dbo].[signals](
# 	[id] [int] IDENTITY(1,1) NOT NULL,
# 	[symbol] [nvarchar](50) NOT NULL,
# 	[signal_type] [nvarchar](10) NOT NULL,
# 	[entry_point] [float] NOT NULL,
# 	[stop_loss] [float] NOT NULL,
# 	[take_profit] [float] NULL,
# 	[sentiment] [float] NULL,
# 	[is_open] [bit] NULL,
# 	[total_profit] [float] NULL,
# 	[created_at] [datetime] NULL,
# 	[updated_at] [datetime] NULL,
# PRIMARY KEY CLUSTERED 
# (
# 	[id] ASC
# )WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
# ) ON [PRIMARY]
# GO

# ALTER TABLE [dbo].[signals] ADD  DEFAULT ((1)) FOR [is_open]
# GO

# ALTER TABLE [dbo].[signals] ADD  DEFAULT (getdate()) FOR [created_at]
# GO

# ALTER TABLE [dbo].[signals] ADD  DEFAULT (getdate()) FOR [updated_at]
# GO




import pyodbc
from datetime import datetime

# SQL Server connection settings
server = 'localhost'
database = 'Stocks'
username = ''
password = ''
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

def create_connection():
    return pyodbc.connect(connection_string)

def create_tables():
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='signals' AND xtype='U')
            CREATE TABLE signals (
                id INT PRIMARY KEY IDENTITY(1,1),
                symbol NVARCHAR(50) NOT NULL,
                signal_type NVARCHAR(10) NOT NULL,
                entry_point FLOAT NOT NULL,
                stop_loss FLOAT NOT NULL,
                take_profit FLOAT,
                sentiment FLOAT,
                is_open BIT DEFAULT 1,
                total_profit FLOAT,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE()
            );
        ''')
        conn.commit()

def save_signal(symbol, signal_type, entry_point, stop_loss, sentiment, take_profit=None):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signals (symbol, signal_type, entry_point, stop_loss, take_profit, sentiment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, signal_type, entry_point, stop_loss, take_profit, sentiment))
        conn.commit()

def update_signal(signal_id, total_profit, is_open):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE signals
            SET total_profit = ?, is_open = ?, updated_at = GETDATE()
            WHERE id = ?
        ''', (total_profit, is_open, signal_id))
        conn.commit()

def fetch_signals():
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signals')
        return cursor.fetchall()
