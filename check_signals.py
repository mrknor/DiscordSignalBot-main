import asyncio
from datetime import datetime
import pytz
from database import fetch_open_signals, update_signal, update_signal_stop_loss
from secret import Secret
import discord
from pytz import timezone
from click_trader import setup_and_click

utc = timezone('UTC')
central = timezone('US/Central')

# Initialize Discord channel and timestamp variables
channel = None
utc_dt = None
central_dt = None
timestamp = None

async def init_globals(bot):
    global channel, utc_dt, central_dt, timestamp
    channel = bot.get_channel(Secret.signal_channel_id)
    utc_dt = datetime.now(utc)
    central_dt = utc_dt.astimezone(central)
    timestamp = central_dt.strftime('%m-%d-%Y %H:%M:%S')

async def check_and_update_signals(bot, equity_agg):
    await init_globals(bot)  # Initialize global variables

    signals = fetch_open_signals()
    latest_price = equity_agg.close

    for signal in signals:
        if signal.is_open:
            risk = abs(signal.entry_point - signal.stop_loss)
            if signal.signal_type == 'LONG':
                if equity_agg.low <= signal.stop_loss:
                    signal.total_profit = round(signal.stop_loss - signal.entry_point, 2)
                    await send_stoploss_hit_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                    setup_and_click('SHORT')  # Execute trade to close long position
                elif latest_price >= signal.take_profit:
                    signal.total_profit = round(signal.take_profit - signal.entry_point, 2)
                    await send_take_profit_hit_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                    setup_and_click('SHORT')  # Execute trade to close long position
                elif latest_price - signal.entry_point >= risk:
                    signal.stop_loss = signal.entry_point  # Move stop loss to break even
                    update_signal_stop_loss(signal.id, signal.entry_point)
            elif signal.signal_type == 'SHORT':
                if equity_agg.high >= signal.stop_loss:
                    signal.total_profit = round(signal.entry_point - signal.stop_loss, 2)
                    await send_stoploss_hit_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                    setup_and_click('LONG')  # Execute trade to close short position
                elif latest_price <= signal.take_profit:
                    signal.total_profit = round(signal.entry_point - signal.take_profit, 2)
                    await send_take_profit_hit_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                    setup_and_click('LONG')  # Execute trade to close short position
                elif signal.entry_point - latest_price >= risk:
                    signal.stop_loss = signal.entry_point  # Move stop loss to break even
                    update_signal_stop_loss(signal.id, signal.entry_point)
        else:
            if signal.signal_type == 'LONG':
                if equity_agg.high >= signal.invalidated_price:
                    await send_invalidated_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                elif latest_price >= signal.entry_point:
                    await send_filled_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=True, invalidated=0)
            elif signal.signal_type == 'SHORT':
                if equity_agg.low <= signal.invalidated_price:
                    await send_invalidated_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=False, invalidated=1)
                elif latest_price <= signal.entry_point:
                    await send_filled_message(signal)
                    update_signal(signal.id, signal.total_profit, is_open=True, invalidated=0)

async def send_stoploss_hit_message(signal):
    message = f"STOPLOSS HIT [{signal.symbol}] at {signal.stop_loss} for total loss of {signal.total_profit:.2f} | {timestamp}"
    await channel.send(message)

async def send_filled_message(signal):
    message = f"FILLED {signal.signal_type} [{signal.symbol}] at {signal.entry_point} | {timestamp}"
    await channel.send(message)

async def send_invalidated_message(signal):
    message = f"INVALIDATED {signal.signal_type} [{signal.symbol}] at {signal.invalidated_price} | {timestamp}"
    await channel.send(message)

async def send_take_profit_hit_message(signal):
    message = f"TAKE PROFIT HIT [{signal.symbol}] at {signal.take_profit} for a total profit of {signal.total_profit:.2f} | {timestamp}"
    await channel.send(message)

async def send_six_minute_update(bot, latest_price):
    await init_globals(bot)  # Initialize global variables

    signals = fetch_open_signals()
    for signal in signals:
        pl = round((latest_price - signal.entry_point), 2) if signal.signal_type == 'LONG' else round((signal.entry_point - latest_price), 2)

        message = f"6 MINUTE UPDATE [{signal.symbol}] P/L: {pl:.2f} | {timestamp}"
        await channel.send(message)
