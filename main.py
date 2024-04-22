import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands, tasks
import discord
from secret import Secret
import asyncio
from datetime import datetime, timedelta
from polygon import WebSocketClient
from polygon.websocket.models import WebSocketMessage
from typing import List
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

client = WebSocketClient("RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG") # hardcoded api_key is used

# docs
# https://polygon.io/docs/stocks/ws_stocks_am
# https://polygon-api-client.readthedocs.io/en/latest/WebSocket.html#


CANDLE_SIZES = [6, 55]
aggregate_data = {size: {} for size in CANDLE_SIZES}
last_data_points = {} 
last_data_time = None 

# aggregates (per minute)
# client.subscribe("AM.*") # all aggregates
client.subscribe("AM.SPY") # single ticker
# client.subscribe("AM.QQQ") # single ticker
# client.subscribe("AM.AAPL") # single ticker
# client.subscribe("AM.TSLA") # single ticker
# client.subscribe("AM.MSFT") # single ticker
# client.subscribe("AM.AMZN") # single ticker
# client.subscribe("AM.META") # single ticker
# client.subscribe("AM.IWM") # single ticker
# client.subscribe("AM.NVDA") # single ticker
# client.subscribe("AM.JPM") # single ticker
# client.subscribe("AM.ABNB") # single ticker
# client.subscribe("AM.AMD") # single ticker

# aggregates (per second)
# client.subscribe("A.*")  # all aggregates
# client.subscribe("A.TSLA") # single ticker


async def run_at_specific_time(task, hour, minute):
    now = datetime.now()
    target_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If the target time is already passed, schedule for the next day
    if target_time < now:
        target_time += timedelta(days=1)
    
    delay = (target_time - now).total_seconds()
    # print(f"Waiting for {delay} seconds until {hour}:{minute} to run the task.")
    
    # await asyncio.sleep(delay)
    await task()


async def handle_msg(msgs: List[WebSocketMessage]):
    global last_data_points, aggregate_data

    for equity_agg in msgs:
        ticker = equity_agg['ticker']

        for size in CANDLE_SIZES:
            if ticker not in aggregate_data[size]:
                aggregate_data[size][ticker] = []

            aggregate_data[size][ticker].append(equity_agg)

            if len(aggregate_data[size][ticker]) == size:
                aggregated_candle = aggregate_candles(aggregate_data[size][ticker])
                aggregate_data[size][ticker] = []  # Reset after aggregation

                if ticker in last_data_points and size in last_data_points[ticker]:
                    previous_candle = last_data_points[ticker][size]

                    # Analyze for shorts and check volume
                    analysis_result_short = analyze_for_shorts(previous_candle, aggregated_candle, ticker)
                    if analysis_result_short:
                        volume = aggregated_candle['v'] > previous_candle['v']
                        message = format_message_short(analysis_result_short, size, volume)
                        await bot.get_channel(Secret.signal_channel_id).send(message)

                    # Analyze for longs and check volume
                    analysis_result_long = analyze_for_longs(previous_candle, aggregated_candle, ticker)
                    if analysis_result_long:
                        volume = aggregated_candle['v'] > previous_candle['v']
                        message = format_message_long(analysis_result_long, size, volume)  # Correct variable reference
                        await bot.get_channel(Secret.signal_channel_id).send(message)

                # Update last data points
                if ticker not in last_data_points:
                    last_data_points[ticker] = {}
                last_data_points[ticker][size] = aggregated_candle

                print(f"{ticker} aggregated data for {size}-minute candle: {aggregated_candle} {datetime.now()}")



def aggregate_candles(candles):
    open_price = candles[0]['o']
    close_price = candles[-1]['c']
    high_price = max(candle['h'] for candle in candles)
    low_price = min(candle['l'] for candle in candles)
    volume = sum(candle['v'] for candle in candles)
    timestamp = candles[-1]['t']

    aggregated_candle = {
        'o': open_price,
        'c': close_price,
        'h': high_price,
        'l': low_price,
        'v': volume,
        't': timestamp
    }

    return aggregated_candle


utc = timezone('UTC')
central = timezone('US/Central')

def format_message_short(analysis_result, candle_size, volume):
    volume_text = "[VC]" if volume else ""

    # Convert UTC timestamp to Central Time
    utc_dt = datetime.fromtimestamp(analysis_result['timestamp'] / 1000, utc)
    central_dt = utc_dt.astimezone(central)
    timestamp = central_dt.strftime('%Y-%m-%d %H:%M:%S')
    return f"{volume_text}[{candle_size} Minute] SHORT Alert: {analysis_result['ticker']}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"

def format_message_long(analysis_result, candle_size, volume):
    volume_text = "[VC]" if volume else ""

    # Similarly adjust for the long message formatting
    utc_dt = datetime.fromtimestamp(analysis_result['timestamp'] / 1000, utc)
    central_dt = utc_dt.astimezone(central)
    timestamp = central_dt.strftime('%Y-%m-%d %H:%M:%S')
    return f"{volume_text}[{candle_size} Minute] LONG Alert: {analysis_result['ticker']}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"


def analyze_for_shorts(data_point_1, data_point_2, symbol):
    is_sender = False
    recent_candle = data_point_2
    prev_candle = data_point_1
    
    # Determine if the last candle is a sender candle
    
    if recent_candle['h'] > prev_candle['h']: # and recent_candle['v'] > prev_candle['v']
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
            'stop_loss': recent_candle['h'],  # Assuming this is how you access high price
            'timestamp': recent_candle['t']  # Include the timestamp from the aggregated candle
        }
    return None



def analyze_for_longs(data_point_1, data_point_2, symbol):
    is_sender = False
    recent_candle = data_point_2
    prev_candle = data_point_1
    
    # Determine if the last candle is a sender candle
    
    if recent_candle['l'] < prev_candle['l'] : # and recent_candle['v'] > prev_candle['v']
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
            'stop_loss': recent_candle['h'],  # Assuming this is how you access high price
            'timestamp': recent_candle['t']  # Include the timestamp from the aggregated candle
        }
    return None


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    # Start the simulation when the bot is ready
    asyncio.create_task(start_client())

async def start_client():
    print(f"Starting WebSocket client at {datetime.now().time()}")
    # Ensure that this async function properly handles the WebSocket connection
    await client.connect(handle_msg)

if __name__ == "__main__":
    bot.run(Secret.token)

