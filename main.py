import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands, tasks
import discord
from secret import Secret
import asyncio
from datetime import datetime, timedelta
from sentiment_analysis import get_headlines_and_sentiments
import numpy as np  # for numerical operations
from database import create_tables, save_signal, update_signal

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

create_tables()

# Calculate the next 2:45 PM CST
def start_time():
    cst = pytz.timezone("US/Central")
    now = datetime.now(cst)
    target_time = now.replace(hour=14, minute=45, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
    return target_time

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    next_run = start_time()  # Calculate the initial start time
    initial_delay = (next_run - datetime.now(pytz.timezone("US/Central"))).total_seconds()  # Calculate the delay in seconds
    print(f"Next run scheduled for: {next_run}")  # Log the initial run time
    
    # Sleep for the initial delay before starting the task
    # await asyncio.sleep(initial_delay)
    
    check_and_alert.change_interval(seconds=86400)  # Set the interval to 24 hours
    check_and_alert.start()  # Start the task

def fetch_ohlc_data(symbol, start_date, end_date, interval, api_key):
    timespan = "day"  
    multiplier = "1"  
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Check if 'results' key exists in the JSON response
        if 'results' in data:
            return data['results']
        else:
            return []  # Return an empty list if 'results' key is not found
    else:
        print(f"Failed to fetch data for {symbol}: {response.text}")
        return None


@tasks.loop(count=1)
async def check_and_alert():
    api_key = "RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG"
    # symbols = [
    #     "SPY", "QQQ", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "AMD", "ZM", 
    #     "WMT", "JPM", "SPOT", "RBLX", "RDDT", "DIS", "NVDA", "ABNB", "PYPL", 
    #     "SNAP", "IWM", "ADBE", "NFLX", "HOOD"
    # ]
    symbols = [
        "TSLA"
    ]
    backtest_mode = True  # Set to True for backtesting, False for live alerts
    backtest_days = 100   # Number of days to backtest

    # Define Eastern Time Zone
    eastern = pytz.timezone('US/Eastern')
    # Get yesterday's date in Eastern Time to ensure completeness of the last trading day's data
    end_date = datetime.now(eastern)
    if backtest_mode:
        start_date = end_date - timedelta(days=backtest_days)
    else:
        start_date = end_date - timedelta(days=1)
    
    for symbol in symbols:
        if backtest_mode:
            # In backtest mode, start from the end date and go backwards
            current_date = end_date
            while current_date > start_date:
                current_start_date = current_date - timedelta(days=1)
                current_start_date_str = current_start_date.strftime('%Y-%m-%d')
                current_end_date_str = current_date.strftime('%Y-%m-%d')
                ohlc_data = fetch_ohlc_data(symbol, current_start_date_str, current_end_date_str, "1", api_key)

                if len(ohlc_data) >= 2:
                    # Process the last two points of OHLC data
                    await process_data_point(ohlc_data[-2], ohlc_data[-1], symbol)

                # Move to the previous day
                current_date -= timedelta(days=1)
        else:
            # Live mode, only process the most recent data
            current_end_date = end_date
            current_start_date_str = start_date.strftime('%Y-%m-%d')
            current_end_date_str = current_end_date.strftime('%Y-%m-%d')
            ohlc_data = fetch_ohlc_data(symbol, current_start_date_str, current_end_date_str, "1", api_key)

            if len(ohlc_data) >= 2:
                await process_data_point(ohlc_data[-2], ohlc_data[-1], symbol)
            else:
                start_date -= timedelta(days=1)


    print("Analysis complete for all symbols.")
    if not backtest_mode:
        next_run = datetime.now() + timedelta(seconds=86400)  # Calculate the next scheduled run
        print(f"Next run is scheduled for: {next_run}")


async def process_data_point(data_point_1, data_point_2, symbol):
    print(f"Analyzing {symbol}...")

    print(f"Testing {symbol} short...")

  

async def process_data_point(data_point_1, data_point_2, symbol):
    print(f"Analyzing {symbol}...")
    # Analyze for potential short positions
    analysis_result = analyze_for_shorts(data_point_1, data_point_2, symbol)
    if analysis_result:
        # Fetch sentiment results and calculate average sentiment
        sentiment_results = get_headlines_and_sentiments(f"https://stockanalysis.com/stocks/{symbol}")
        sentiment_scores = [sent[1] for sent in sentiment_results if sent[1] is not None]
        if sentiment_scores:
            average_sentiment = np.mean(sentiment_scores)
            print(f"Average sentiment for {symbol}: {average_sentiment}")

            # Check sentiment range to determine if it's outside neutral range
            tag = "[SC] " if average_sentiment < 4.5 else ""
            timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
            message = f"{tag}Daily Swing SHORT Alert: {symbol}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"
            print(message)
            # await bot.get_channel(Secret.signal_channel_id).send(message)
            save_signal(symbol, 'SHORT', analysis_result['entry_point'], analysis_result['stop_loss'], average_sentiment, take_profit=None)
        
        else:
            print(f"No sentiment scores available for {symbol}.")
            timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
            message = f"Daily Swing SHORT Alert: {symbol}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"
            print(message)
            # await bot.get_channel(Secret.signal_channel_id).send(message)
            save_signal(symbol, 'SHORT', analysis_result['entry_point'], analysis_result['stop_loss'], None, take_profit=None)
    
    else:
        print(f"No short detected.")
        
    # Analyze for potential long positions
    analysis_result_long = analyze_for_longs(data_point_1, data_point_2, symbol)
    if analysis_result_long:
        # Fetch sentiment results and calculate average sentiment
        sentiment_results = get_headlines_and_sentiments(f"https://stockanalysis.com/stocks/{symbol}")
        sentiment_scores = [sent[1] for sent in sentiment_results if sent[1] is not None]
        if sentiment_scores:
            average_sentiment = np.mean(sentiment_scores)
            print(f"Average sentiment for {symbol}: {average_sentiment}")

            # Check sentiment range to determine if it's outside neutral range
            tag = "[SC] " if average_sentiment > 5.5 else ""
            timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
            message = f"{tag}Daily Swing LONG Alert: {symbol}, Entry: {analysis_result_long['entry_point']}, Stop: MANAGE YOUR TRADE | {timestamp}"
            print(message)
            # await bot.get_channel(Secret.signal_channel_id).send(message)
            save_signal(symbol, 'LONG', analysis_result_long['entry_point'], analysis_result_long['stop_loss'], average_sentiment, take_profit=None)
    
        else:
            print(f"No sentiment scores available for {symbol}.")
            timestamp = (datetime.fromtimestamp(data_point_2['t'] / 1000) + timedelta(days=1)).strftime('%m-%d-%Y')
            message = f"Daily Swing LONG Alert: {symbol}, Entry: {analysis_result_long['entry_point']}, Stop: MANAGE YOUR TRADE | {timestamp}"
            print(message)
            # await bot.get_channel(Secret.signal_channel_id).send(message)
            save_signal(symbol, 'LONG', analysis_result_long['entry_point'], analysis_result_long['stop_loss'], None, take_profit=None)

    else:
        print(f"No long detected.")



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