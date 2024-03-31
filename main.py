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

client = WebSocketClient("RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG") # hardcoded api_key is used
# client = WebSocketClient()  # POLYGON_API_KEY environment variable is used

# docs
# https://polygon.io/docs/stocks/ws_stocks_am
# https://polygon-api-client.readthedocs.io/en/latest/WebSocket.html#

# aggregates (per minute)
# client.subscribe("AM.*") # all aggregates
client.subscribe("AM.TSLA") # single ticker

# aggregates (per second)
# client.subscribe("A.*")  # all aggregates
# client.subscribe("A.TSLA") # single ticker

# trades
# client.subscribe("T.*")  # all trades
# client.subscribe("T.TSLA", "T.UBER") # multiple tickers

# quotes
# client.subscribe("Q.*")  # all quotes
# client.subscribe("Q.TSLA", "Q.UBER") # multiple tickers



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

async def start_client():
    print(f"Starting client at {datetime.now().time()}")
    client.run(handle_msg)

last_data_points = {}  # Dictionary to hold the last two data points for each ticker
last_data_time = None  # Keeps track of the last data processing time
aggregate_data = {}  # Temporary storage for the 5-minute aggregated data

async def handle_msg(msgs: List[WebSocketMessage]):
    global last_data_points, aggregate_data

    for m in msgs:
        # Extracting the necessary data from the message
        ticker = m['ticker']
        if ticker not in aggregate_data:
            aggregate_data[ticker] = []

        aggregate_data[ticker].append(m)

        # Check if we have five data points to aggregate
        if len(aggregate_data[ticker]) == 5:
            # Aggregate the data points
            aggregated_candle = aggregate_candles(aggregate_data[ticker])
            # Clear the stored data points for this ticker
            aggregate_data[ticker] = []

            # If there's a previous data point to compare with, perform analysis
            if ticker in last_data_points and last_data_points[ticker]:
                previous_candle = last_data_points[ticker]
                # Perform analysis for shorts and longs
                analysis_result_short = analyze_for_shorts(previous_candle, aggregated_candle, ticker)
                if analysis_result_short:
                    message = format_message_short(analysis_result_short)
                    await bot.get_channel(Secret.signal_channel_id).send(message)

                analysis_result_long = analyze_for_longs(previous_candle, aggregated_candle, ticker)
                if analysis_result_long:
                    message = format_message_long(analysis_result_long)
                    await bot.get_channel(Secret.signal_channel_id).send(message)

            # Store the aggregated candle as the last data point for future comparison
            last_data_points[ticker] = aggregated_candle

def aggregate_candles(candles):
    """
    Aggregates five one-minute candles into a single five-minute candle.
    """
    # Initialize aggregation variables
    open_price = candles[0]['o']
    close_price = candles[-1]['c']
    high_price = max(candle['h'] for candle in candles)
    low_price = min(candle['l'] for candle in candles)
    volume = sum(candle['v'] for candle in candles)
    
    # Calculate the weighted average price (optional, based on your needs)
    # vw_sum = sum(candle['v'] * candle['vw'] for candle in candles)
    # vw_avg = vw_sum / volume if volume else 0

    # Construct the aggregated candle
    aggregated_candle = {
        'o': open_price,
        'c': close_price,
        'h': high_price,
        'l': low_price,
        'v': volume,
        # 'vw': vw_avg,  # Include if needed
    }

    return aggregated_candle


# Helper functions to format messages
def format_message_short(analysis_result):
    timestamp = datetime.fromtimestamp(analysis_result['data_point_2']['t'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return f"SHORT Alert: {analysis_result['ticker']}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"

def format_message_long(analysis_result):
    timestamp = datetime.fromtimestamp(analysis_result['data_point_2']['t'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return f"LONG Alert: {analysis_result['ticker']}, Entry: {analysis_result['entry_point']}, Stop: {analysis_result['stop_loss']} | {timestamp}"


intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)


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

# Ensure this part is run inside an asyncio event loop
async def main():
    await run_at_specific_time(start_client, 7, 57)

# Start the main coroutine
if __name__ == "__main__":
    asyncio.run(main())
