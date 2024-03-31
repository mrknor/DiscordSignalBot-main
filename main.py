import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands, tasks
import discord
from secret import Secret
import asyncio
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)
use_historical_data = True  # Set to False for live data


# Schedule the task and start the bot
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    check_and_alert.start()



def fetch_ohlc_data(symbol, start_date, end_date, interval, api_key):
    # Correcting interval and timespan
    timespan = "day"  # For minute data
    multiplier = "1"  # For 1-minute intervals
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    else:
        print(f"Failed to fetch data for {symbol}: {response.text}")
        return None



@tasks.loop(count=1)
async def check_and_alert():
    api_key = "RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG"
    symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "AMD", "ZM", "WMT",
       "JPM", "SPOT", "RBLX", "RDDT", "DIS", "NVDA", "ABNB", "PYPL", "SNAP", "IWM",
       "ADBE", "NFLX", "HOOD"
       ]
    # symbols = ["RIVN"
    #     ]
    intervals = ["1"]  # Representing the intervals as needed by Polygon.io
    
    if use_historical_data:
        start_date = "2024-03-27"  # Example start date for historical data
        end_date = "2024-03-29"  # Example end date for historical data
    else:
        now = datetime.now(pytz.timezone('US/Eastern'))
        start_date = end_date = now.strftime('%Y-%m-%d')
    
    # Loop through each symbol
    for symbol in symbols:
        # Check both intervals for each symbol
        for interval_value in intervals:
            # Fetch OHLC data for the current interval
            ohlc_data = fetch_ohlc_data(symbol, start_date, end_date, interval_value, api_key)
            if ohlc_data:

                if use_historical_data:
                    # Iterate through each data point for historical testing
                    for i in range(0, len(ohlc_data) - 1):
                        await process_data_point(ohlc_data[i], ohlc_data[i+1], symbol)

                else:
                    # For live data, process only the latest data point
                    await process_data_point([ohlc_data[0], ohlc_data[1]], symbol)
            await asyncio.sleep(3)
    
    print(f"No more symbols.")

async def process_data_point(data_point_1, data_point_2, symbol):
    print(f"Analyzing {symbol}...")
    await asyncio.sleep(2)
    print(f"Testing {symbol} short...")
    await asyncio.sleep(2)
    analysis_result = analyze_for_shorts(data_point_1, data_point_2, symbol)  # Assuming analyze_for_reversal expects a list of OHLC data points
    if analysis_result:
        timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
        message = f"SHORT Alert: {symbol}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"
        print(message)
        await bot.get_channel(Secret.signal_channel_id).send(message)
        await asyncio.sleep(2)
    else:
        print(f"No short detected.")
        await asyncio.sleep(2)

    print(f"Testing {symbol} long...")
    await asyncio.sleep(2)
    analysis_result_long = analyze_for_longs(data_point_1, data_point_2, symbol)  # Assuming analyze_for_reversal expects a list of OHLC data points
    if analysis_result_long:
        timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
        message = f"LONG Alert: {symbol}, Entry: {analysis_result_long['entry_point']}, Stop: MANAGE YOUR TRADE | {timestamp}"
        print(message)
        await bot.get_channel(Secret.signal_channel_id).send(message)
        await asyncio.sleep(2)
    else:
        print(f"No long detected.")
        await asyncio.sleep(2)

def analyze_for_shorts(data_point_1, data_point_2, symbol):
    is_sender = False
    recent_candle = data_point_2
    prev_candle = data_point_1
    
    # Determine if the last candle is a sender candle
    
    if recent_candle['h'] > prev_candle['h']:
        #green candle first
        #red candle secondary
        if recent_candle['c'] < recent_candle['o']:
            if recent_candle['c'] < prev_candle['c']:
                entry_point = recent_candle['o']
                is_sender = True
            if recent_candle['l'] < prev_candle['l']:
                is_sender = False
        #green candle secondary
        if recent_candle['c'] > recent_candle['o']:
            if recent_candle['c'] < prev_candle['c']:
                entry_point = recent_candle['c']
                is_sender = True
            if recent_candle['l'] < prev_candle['l']:
                is_sender = False
    if is_sender:
        return {
            'ticker': symbol,
            'entry_point': entry_point,
            'stop_loss': recent_candle['h']
        }
    return None


def analyze_for_longs(data_point_1, data_point_2, symbol):
    is_sender = False
    recent_candle = data_point_2
    prev_candle = data_point_1
    
    # Determine if the last candle is a sender candle
    
    if recent_candle['l'] < prev_candle['l']:
        #red candle first
        #green candle secondary
        if recent_candle['o'] < recent_candle['c']:
            if recent_candle['c'] < prev_candle['o']:
                entry_point = prev_candle['h']
                is_sender = True
            if recent_candle['h'] > prev_candle['h']:
                is_sender = False
        #red candle secondary
        if recent_candle['o'] > recent_candle['c']:
            if recent_candle['c'] > prev_candle['c']:
                entry_point = prev_candle['h']
                is_sender = True
            if recent_candle['h'] > prev_candle['h']:
                is_sender = False
    if is_sender:
        return {
            'ticker': symbol,
            'entry_point': entry_point,
            'stop_loss': recent_candle['l']
        }
    return None

   
bot.run(Secret.token)