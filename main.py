import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands, tasks
import discord
from secret import Secret

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
    timespan = "minute"  # For minute data
    multiplier = "1"  # For 1-minute intervals
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    else:
        print(f"Failed to fetch data for {symbol}: {response.text}")
        return None



@tasks.loop(seconds=20 if use_historical_data else 60)
async def check_and_alert():
    api_key = "RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG"
    symbols = ["AAPL"]  # Your symbols of interest
    intervals = ["1"]  # Representing the intervals as needed by Polygon.io
    
    if use_historical_data:
        start_date = "2024-03-01"  # Example start date for historical data
        end_date = "2024-03-03"  # Example end date for historical data
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
                    for i in range(1, len(ohlc_data)):
                        process_data_point([ohlc_data[i], ohlc_data[i-1]], symbol)

                else:
                    # For live data, process only the latest data point
                    process_data_point([ohlc_data[-1], ohlc_data[-2]], symbol)

async def process_data_point(data_point, symbol):
    # Analyze the data point
    analysis_result = analyze_for_reversal([data_point])
    if analysis_result:
        timestamp = datetime.fromtimestamp(data_point['t'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] {symbol} signal: {analysis_result['signal']} at {analysis_result['entry_point']}, Stop-loss: {analysis_result['stop_loss']}"
        await bot.get_channel(Secret.signal_channel_id).send(message)

def analyze_for_reversal(ohlc_data):
    """
    Analyze OHLC data to find reversal candlestick patterns.
    
    :param ohlc_data: List of dictionaries, each containing OHLC data for a single candlestick
    :return: Dictionary with signal information, or None if no pattern is detected
    """
    print(f"Inside analyze_for_reversal")
    if len(ohlc_data) < 2:
        print(f"Not enough data: {len(ohlc_data)}")
        return None  # Not enough data to identify the pattern
    
    # Assuming ohlc_data is sorted in ascending order by time
    last_candle = ohlc_data[-1]
    prev_candle = ohlc_data[-2]
    

    print(f"Checking data: {last_candle}")
    # Determine if the last candle is a sender candle
    is_sender = False
    if last_candle['h'] > prev_candle['h'] and (last_candle['c'] < last_candle['o'] if last_candle['c'] > prev_candle['c'] else last_candle['c'] <= last_candle['o']):
        is_sender = True

    print(f"Checking data: {last_candle['c']}")

    if is_sender:
        # Determine the entry point based on the color of the sender candle
        entry_point = last_candle['c'] if last_candle['c'] < last_candle['o'] else last_candle['o']
        return {
            'ticker': 'Symbol_Name',  # Replace with actual symbol
            'entry_point': entry_point,
            'signal': 'SELL' if last_candle['c'] > last_candle['o'] else 'BUY',  # Assuming a reversal to downtrend
            'stop_loss': last_candle['h']  # Add this line
        }

    return None

   
bot.run(Secret.token)