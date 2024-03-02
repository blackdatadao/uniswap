# !/usr/bin/env python

import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

config_logging(logging, logging.DEBUG)

def get_kline_data_from_binance(symbol, interval, limit):
    spot_client = Client(base_url="https://testnet.binance.vision")
    kline_data = spot_client.klines(symbol, interval, limit=limit)
    kline_data = pd.DataFrame(kline_data)
    kline_data.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
    kline_data['Open Time'] = pd.to_datetime(kline_data['Open Time'], unit='ms')
    kline_data['Close Time'] = pd.to_datetime(kline_data['Close Time'], unit='ms')
    kline_data['Open'] = kline_data['Open'].astype(float)
    kline_data['High'] = kline_data['High'].astype(float)
    kline_data['Low'] = kline_data['Low'].astype(float)
    kline_data['Close'] = kline_data['Close'].astype(float)
    return kline_data

def reverse_price(kline_data):
    kline_data['Open'] = 1 / kline_data['Open']
    kline_data['High'] = 1 / kline_data['High']
    kline_data['Low'] = 1 / kline_data['Low']
    kline_data['Close'] = 1 / kline_data['Close']
    return kline_data

spot_client = Client(base_url="https://testnet.binance.vision")

# logging.info(spot_client.klines("BTCUSDT", "1m"))
x=spot_client.klines("ARBETH", "4h", limit=10)
#convert to dateframe

df=pd.DataFrame(x)
df.columns=['Open Time','Open','High','Low','Close','Volume','Close Time','Quote Asset Volume','Number of Trades','Taker buy base asset volume','Taker buy quote asset volume','Ignore']
df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
#convert price data to 1/the actual price
df['Open']=1/df['Open'].astype(float)
df['High']=1/df['High'].astype(float)
df['Low']=1/df['Low'].astype(float)
df['Close']=1/df['Close'].astype(float)
#create a candlestick chart

fig = go.Figure(data=[go.Candlestick(x=df['Open Time'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'])])
#show the fig
fig.show()



c=1

# from binance.spot import Spot

# client = Spot()

# # Get server timestamp
# print(client.time())
# # Get klines of BTCUSDT at 1m interval
# print(client.klines("BTCUSDT", "1m"))
# # Get last 10 klines of BNBUSDT at 1h interval
# print(client.klines("BNBUSDT", "1h", limit=10))