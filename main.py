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
import numpy as np
from scipy.signal import argrelextrema


intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

candlestick_data = {}



# Function to determine directional bias
def determine_directional_bias(data):
    if data['current_price'] > data['yesterday_close']:
        return 'Bullish', data['low']  # swing low in bullish scenario
    else:
        return 'Bearish', data['high']  # swing high in bearish scenario


def calculate_fibonacci_levels(high, low):
    """Calculates Fibonacci retracement levels between a high and a low."""
    diff = high - low
    return {
        '0': high,
        '0.5': low + 0.5 * diff,
        '0.62': low + 0.618 * diff,
        '0.705': low + 0.705 * diff,
        '0.79': low + 0.79 * diff,
        '1': low
    }

def check_breakouts_and_ote(bias, swing_highs, swing_lows, current_price):
    """Check for breakouts and calculate Optimal Trade Entry (OTE) based on Fibonacci levels."""
    if bias == 'Bullish' and swing_lows:
        last_low = swing_lows[-1]
        if swing_highs:  # Make sure there is at least one swing high to calculate from
            last_high = swing_highs[-1]
            fib_levels = calculate_fibonacci_levels(last_high['h'], last_low['l'])
            # Check if current price is within the OTE zone
            if fib_levels['0.62'] <= current_price <= fib_levels['0.79']:
                ote = fib_levels['0.79']  # Use the upper boundary of the OTE zone for entry
                return True, ote
    elif bias == 'Bearish' and swing_highs:
        last_high = swing_highs[-1]
        if swing_lows:  # Make sure there is at least one swing low to calculate from
            last_low = swing_lows[-1]
            fib_levels = calculate_fibonacci_levels(last_high['h'], last_low['l'])
            # Check if current price is within the OTE zone
            if fib_levels['0.79'] >= current_price >= fib_levels['0.62']:
                ote = fib_levels['0.79']  # Use the lower boundary of the OTE zone for entry
                return True, ote
    return False, None



# Function to send a signal to Discord
async def send_signal_to_discord(message):
    channel = bot.get_channel(Secret.signal_channel_id)
    await channel.send(message)


async def fetch_historical_minute_data(symbol, start_date, end_date, interval, api_key):
    # Assuming API allows fetching minute-level data
    timespan = "minute"  
    multiplier = "1"  
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        print(f"Failed to fetch data for {symbol}: {response.text}")
        return []



def find_swing_points(data, window_size=5):
    highs = [data[i]['h'] for i in range(len(data))]
    lows = [data[i]['l'] for i in range(len(data))]
    max_indices = argrelextrema(np.array(highs), np.greater_equal, order=window_size)[0]
    min_indices = argrelextrema(np.array(lows), np.less_equal, order=window_size)[0]
    swing_highs = [data[i] for i in max_indices]
    swing_lows = [data[i] for i in min_indices]
    return swing_highs, swing_lows

def determine_market_bias(swing_highs, swing_lows):
    """Determine market bias based on recent swing highs and swing lows."""
    if not swing_highs or not swing_lows:
        return 'Neutral'  # Not enough data to determine bias

    # Check the most recent swings to determine the trend
    if len(swing_highs) > 1 and len(swing_lows) > 1:
        # Compare the last two swing highs and the last two swing lows
        recent_high_trend = swing_highs[-1]['h'] > swing_highs[-2]['h']
        recent_low_trend = swing_lows[-1]['l'] > swing_lows[-2]['l']

        if recent_high_trend and recent_low_trend:
            return 'Bullish'
        elif not recent_high_trend and not recent_low_trend:
            return 'Bearish'

    # If trends are mixed or not enough historical swings, consider the trend neutral or uncertain
    return 'Neutral'




@tasks.loop(minutes=1)
async def market_check():
    api_key = "RG34KJaw5GqpozaHArfsZ7I2P5kAVlmG"
    symbols = ["SPY"]
    start_date = "2024-04-29"
    end_date = "2024-05-10"

    for symbol in symbols:
        if symbol not in candlestick_data:
            candlestick_data[symbol] = []

        print(f"Fetching historical minute data for {symbol}.")
        # Fetch minute-level data for the specified date range
        historical_data = await fetch_historical_minute_data(symbol, start_date, end_date, "minute", api_key)
        
        # Process each minute data point
        for data_point in historical_data:
            candlestick_data[symbol].append(data_point)

            if len(candlestick_data[symbol]) > 10:
                swing_highs, swing_lows = find_swing_points(candlestick_data[symbol])
                current_data = candlestick_data[symbol][-1]
                current_price = current_data['c']
                current_time = datetime.fromtimestamp(current_data['t'] / 1000).strftime('%Y-%m-%d %H:%M')


                # Determine market bias based on the latest price action
                bias = determine_market_bias(swing_highs, swing_lows)

                breakout, ote = check_breakouts_and_ote(bias, swing_highs, swing_lows, current_price)
                if breakout:
                    message = f"{current_time} - {bias} breakout detected at OTE: {ote:.2f}. Current price: {current_price}"
                    # await send_signal_to_discord(message)
                    print(message)

            if len(candlestick_data[symbol]) > 30:
                candlestick_data[symbol] = candlestick_data[symbol][-30:]

        print("Market check task completed.")

    

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    market_check.start()  # Start the market check loop when the bot is ready

if __name__ == "__main__":
    bot.run(Secret.token)
