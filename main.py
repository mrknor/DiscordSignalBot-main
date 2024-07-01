from datetime import datetime
from discord.ext import commands
import discord
from secret import Secret
import asyncio
from polygon import WebSocketClient
from polygon.websocket.models import WebSocketMessage
from typing import List
from pytz import timezone
from database import save_signal
from check_signals import check_and_update_signals, send_six_minute_update  # Import the new methods

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

client = WebSocketClient("IT0kdpKa_FhxCrarFbwRuM57SZPVCfZv") # hardcoded api_key is used

# docs
# https://polygon.io/docs/stocks/ws_stocks_am
# https://polygon-api-client.readthedocs.io/en/latest/WebSocket.html#


CANDLE_SIZES = [6]
aggregate_data = {size: {} for size in CANDLE_SIZES}
last_data_points = {} 
last_data_time = None 

client.subscribe("AM.SPY") # single ticker

async def handle_msg(msgs: List[WebSocketMessage]):
    global last_data_points, aggregate_data

    for equity_agg in msgs:

        

        ticker = equity_agg.symbol

        for size in CANDLE_SIZES:

            # if size == 5 and ticker not in ['SPY', 'QQQ']:
            #     continue  # Skip 5-minute processing for all except SPY and QQQ

            if ticker not in aggregate_data[size]:
                aggregate_data[size][ticker] = []

            aggregate_data[size][ticker].append(equity_agg)

            if len(aggregate_data[size][ticker]) == size:   
                aggregated_candle = aggregate_candles(aggregate_data[size][ticker])

                await send_six_minute_update(bot, aggregated_candle['c'])
                
                aggregate_data[size][ticker] = []  # Reset after aggregation

                if ticker in last_data_points and size in last_data_points[ticker]:
                    previous_candle = last_data_points[ticker][size]

                    # Analyze for shorts and check volume
                    analysis_result_short = analyze_for_shorts(previous_candle, aggregated_candle, ticker)
                    if analysis_result_short:
                        volume = aggregated_candle['v'] > previous_candle['v']
                        message = format_message_short(analysis_result_short, size, volume)
                        await bot.get_channel(Secret.signal_channel_id).send(message)
                        save_signal(ticker, 'SHORT', analysis_result_short['entry_point'], analysis_result_short['stop_loss'], analysis_result_short['invalidated_price'], None, volume, take_profit=None)
        
                    # Analyze for longs and check volume
                    analysis_result_long = analyze_for_longs(previous_candle, aggregated_candle, ticker)
                    if analysis_result_long:
                        volume = aggregated_candle['v'] > previous_candle['v']
                        message = format_message_long(analysis_result_long, size, volume)  # Correct variable reference
                        await bot.get_channel(Secret.signal_channel_id).send(message)
                        save_signal(ticker, 'LONG', analysis_result_long['entry_point'], analysis_result_long['stop_loss'], analysis_result_long['invalidated_price'], None, volume, take_profit=None)
                
                # Update last data points
                if ticker not in last_data_points:
                    last_data_points[ticker] = {}
                last_data_points[ticker][size] = aggregated_candle

                print(f"{ticker} aggregated data for {size}-minute candle: {aggregated_candle} {datetime.now()}")

 
        await check_and_update_signals(bot, equity_agg)


def aggregate_candles(candles):
    open_price = candles[0].open
    close_price = candles[-1].close
    high_price = max(candle.high for candle in candles)
    low_price = min(candle.low for candle in candles)
    volume = sum(candle.volume for candle in candles)
    timestamp = candles[-1].end_timestamp

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
    invalidated_price = None

    if recent_candle['h'] > prev_candle['h']:
        if recent_candle['c'] < recent_candle['o']:
            if recent_candle['c'] < prev_candle['c']:
                entry_point = recent_candle['o']
                invalidated_price = prev_candle['l']
                is_sender = True
            if recent_candle['l'] < prev_candle['l']:
                is_sender = False
        if recent_candle['c'] > recent_candle['o']:
            if recent_candle['c'] < prev_candle['c']:
                entry_point = recent_candle['c']
                invalidated_price = prev_candle['l']
                is_sender = True
            if recent_candle['l'] < prev_candle['l']:
                is_sender = False
    if is_sender:
        return {
            'ticker': symbol,
            'entry_point': entry_point,
            'stop_loss': recent_candle['h'],
            'invalidated_price': invalidated_price,
            'timestamp': recent_candle['t']
        }
    return None

def analyze_for_longs(data_point_1, data_point_2, symbol):
    is_sender = False
    recent_candle = data_point_2
    prev_candle = data_point_1
    invalidated_price = None

    if recent_candle['l'] < prev_candle['l']:
        if recent_candle['o'] < recent_candle['c']:
            if recent_candle['c'] < prev_candle['o']:
                entry_point = recent_candle['o']
                invalidated_price = prev_candle['h'] # maybe change to recent
                is_sender = True
            if recent_candle['h'] > prev_candle['h']:
                is_sender = False
        if recent_candle['o'] > recent_candle['c']:
            if recent_candle['c'] > prev_candle['c']:
                entry_point = recent_candle['c']
                invalidated_price = prev_candle['h']
                is_sender = True
            if recent_candle['h'] > prev_candle['h']:
                is_sender = False
    if is_sender:
        return {
            'ticker': symbol,
            'entry_point': entry_point,
            'stop_loss': recent_candle['l'],
            'invalidated_price': invalidated_price,
            'timestamp': recent_candle['t']
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

