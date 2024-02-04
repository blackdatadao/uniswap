# !/usr/bin/env python

import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
from datetime import datetime

config_logging(logging, logging.DEBUG)

spot_client = Client(base_url="https://testnet.binance.vision")

# logging.info(spot_client.klines("BTCUSDT", "1m"))
x=spot_client.klines("ARBETH", "4h", limit=10)
#convert to dateframe
import pandas as pd
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
import plotly.graph_objects as go
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