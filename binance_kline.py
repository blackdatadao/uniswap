# !/usr/bin/env python

# use package in other directory
path='D:/uniswaptrade/env/Lib/site-packages'
import sys
if path not in sys.path:
    sys.path.append(path)

import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

config_logging(logging, logging.DEBUG)

def get_kline_data_from_binance(symbol, interval, limit,startTime=None,endTime=None):
    spot_client = Client(base_url="http://data-api.binance.vision")
    kline_data = spot_client.klines(symbol, interval, limit=limit,startTime=startTime,endTime=endTime)
    kline_data = pd.DataFrame(kline_data)
    kline_data.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
    kline_data['Open Time'] = pd.to_datetime(kline_data['Open Time'], unit='ms')
    kline_data['Close Time'] = pd.to_datetime(kline_data['Close Time'], unit='ms')
    kline_data['Open'] = kline_data['Open'].astype(float)
    kline_data['High'] = kline_data['High'].astype(float)
    kline_data['Low'] = kline_data['Low'].astype(float)
    kline_data['Close'] = kline_data['Close'].astype(float)
    # check if the high is greater than 10% of the average of the open and close, replace the high with the 110% of the average of the open and close
    kline_data['High'] = kline_data.apply(lambda x: x['High'] if x['High'] < 1.05 * (x['Open']+x['Close'])/2 else 1.0 * (x['Open']+x['Close'])/2, axis=1)
    # check if the low is less than 70% of the average of the open and close, replace the low with the 70% of the average of the open and close
    kline_data['Low'] = kline_data.apply(lambda x: x['Low'] if x['Low'] > 0.95 * (x['Open']+x['Close'])/2 else 1 * (x['Open']+x['Close'])/2, axis=1)
    #average price
    kline_data['average']=kline_data[['Open','High','Low','Close']].mean(axis=1)
    kline_data['normalized_average']=kline_data['average']/kline_data['average'].iloc[0]
    return kline_data

def reverse_price(kline_data):
    kline_data['Open'] = 1 / kline_data['Open']
    kline_data['High'] = 1 / kline_data['High']
    kline_data['Low'] = 1 / kline_data['Low']
    kline_data['Close'] = 1 / kline_data['Close']
    return kline_data



# spot_client = Client(base_url="https://testnet.binance.vision")

# # logging.info(spot_client.klines("BTCUSDT", "1m"))
# x=spot_client.klines("ARBETH", "4h", limit=10)
# #convert to dateframe

# df=pd.DataFrame(x)
# df.columns=['Open Time','Open','High','Low','Close','Volume','Close Time','Quote Asset Volume','Number of Trades','Taker buy base asset volume','Taker buy quote asset volume','Ignore']
# df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
# df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
# #convert price data to 1/the actual price
# df['Open']=1/df['Open'].astype(float)
# df['High']=1/df['High'].astype(float)
# df['Low']=1/df['Low'].astype(float)
# df['Close']=1/df['Close'].astype(float)
# #create a candlestick chart

# fig = go.Figure(data=[go.Candlestick(x=df['Open Time'],
#                 open=df['Open'],
#                 high=df['High'],
#                 low=df['Low'],
#                 close=df['Close'])])
# #show the fig
# fig.show()
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import numpy as np
import pandas as pd

def plot_price_comparison(price_1, price_2, price_1_name,price_2_name):
    """
    Plots the price data for two datasets on a shared x-axis with distinct y-axes.

    Parameters:
    - price_1: DataFrame containing the first set of price data.
    - price_2: DataFrame containing the second set of price data.
    - title: String, the title of the plot.
    Example usage:
        Assuming 'price_1' and 'price_2' are your DataFrame variables with the necessary data
        plot_price_comparison(price_1, price_2, title='1 Hour Price Comparison')
    """
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.02, specs=[[{"secondary_y": True}]])
    
    # Price 1 candlestick trace
    fig.add_trace(go.Candlestick(x=price_1['Open Time'],
                                 open=price_1['Open'],
                                 high=price_1['High'],
                                 low=price_1['Low'],
                                 close=price_1['Close'],name=price_1_name,
                                 increasing={'line': {'color': 'rgba(0, 255, 0,0.4)'}, 'fillcolor': 'rgba(0, 255, 0, 0)'},
                                 decreasing={'line': {'color': 'rgba(255, 0, 0, 0.4)'}, 'fillcolor': 'rgba(255, 0, 0, 0)'}
                                ),
                    secondary_y=False)

    # Price 2 candlestick trace
    fig.add_trace(go.Candlestick(x=price_2['Open Time'],
                                 open=price_2['Open'],
                                 high=price_2['High'],
                                 low=price_2['Low'],
                                 close=price_2['Close'],name=price_2_name),
                  secondary_y=True)

    # Update layout
    fig.update_layout(
        # title=title,
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", xanchor="center", yanchor="bottom", x=0.5, y=-0.5, font=dict(size=24, color="white"))
    )

    fig.update_xaxes(showgrid=False, showline=True, linewidth=2, linecolor='white', tickfont=dict(color='white'))
    fig.update_yaxes(showgrid=False, showline=True, linewidth=2, linecolor='white', tickfont=dict(color='white'), secondary_y=False)
    fig.update_yaxes(showgrid=False, showline=True, linewidth=2, linecolor='white', tickfont=dict(color='white'), secondary_y=True)

    return fig


def calculate_rolling_beta(asset_df, benchmark_df, n, price_column='Close'):
    """
    Calculate rolling beta values for asset compared to a benchmark.

    Parameters:
    - asset_df: DataFrame containing price data for the asset.
    - benchmark_df: DataFrame containing price data for the benchmark.
    - n: The number of data points to use for each beta calculation (rolling window size).
    - price_column: The name of the column in the DataFrames that contains the price data.

    Returns:
    - A Pandas Series containing the beta values for each data point based on the previous n data points.
    """
    
    # Calculate daily returns for both dataframes
    asset_returns = asset_df[price_column].pct_change()
    benchmark_returns = benchmark_df[price_column].pct_change()

    # Initialize a list to store the calculated beta values
    beta_values = [np.nan] * n  # Start with n NaN values to align the beta values with the original DataFrame

    # Loop through the dataset, starting from the n+1 data point
    for i in range(n, len(asset_df)):
        # Select the window of the last n returns for both the asset and the benchmark
        asset_window = asset_returns.iloc[i-n:i]
        benchmark_window = benchmark_returns.iloc[i-n:i]
        
        # Calculate covariance between asset and benchmark returns in the window
        covariance = np.cov(asset_window, benchmark_window)[0, 1]
        
        # Calculate the variance of benchmark returns in the window
        variance = np.var(benchmark_window)
        
        # Calculate beta for the window and append it to the list
        beta = covariance / variance
        beta_values.append(beta)

    # Create a Pandas Series from the list of beta values
    beta_series = pd.Series(beta_values, index=asset_df.index)
    
    return beta_series


def plot_dual_axis_time_series_plotly(time, series1, series2, label1='Series 1', label2='Series 2',
                                      axis1_name='Axis 1', axis2_name='Axis 2', title='Dual Axis Time Series'):
    """
    Plots two data series with a shared x-axis (time) and distinct y-axes using Plotly.

    Parameters:
    - time: Array-like, the common time axis for both data series.
    - series1: Array-like, the first data series to plot.
    - series2: Array-like, the second data series to plot.
    - label1: String, the label for the first data series.
    - label2: String, the label for the second data series.
    - axis1_name: String, the label for the y-axis of the first data series.
    - axis2_name: String, the label for the y-axis of the second data series.
    - title: String, the title of the plot.
    """
    
    # Create a figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Scatter(x=time, y=series1, name=label1, marker_color='cyan'),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=time, y=series2, name=label2, marker_color='magenta'),
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(
        title={
            'text': title,
            'font': {
                'color': 'white'  
            }
        },
        plot_bgcolor='black', 
        paper_bgcolor='black',
        font=dict(color='white'),
        height=600,
        legend=dict(orientation="h", xanchor="center",yanchor="bottom",x=0.5, y=-0.5,font=dict(size=18, color="white"))

    )

    # Set x-axis title
    fig.update_xaxes(title_text="Time", color='white')

    # Set y-axes titles
    fig.update_yaxes(title_text=axis1_name, secondary_y=False, color='cyan')
    fig.update_yaxes(title_text=axis2_name, secondary_y=True, color='magenta')
    return fig

    
def plot_dual_axis_time_series_plotly_three(time, series1, series2, series3, label1='Series 1', label2='Series 2', label3='Series 3',
                                      axis1_name='Axis 1', axis2_name='Axis 2', axis3_name='Axis 3', title='Dual Axis Time Series'):

    # Create a figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Scatter(x=time, y=series1, name=label1, marker_color='cyan'),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=time, y=series2, name=label2, marker_color='magenta'),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(x=time, y=series3, name=label3, marker_color='yellow'),
        secondary_y=True,
    )
    # Add figure title
    fig.update_layout(
        title={
            'text': title,
            'font': {
                'color': 'white'  
            }
        },
        plot_bgcolor='black', 
        paper_bgcolor='black',
        font=dict(color='white'),
        height=600,
        legend=dict(orientation="h", xanchor="center",yanchor="bottom",x=0.5, y=-0.5,font=dict(size=18, color="white"))
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Time", color='white')

    # Set y-axes titles
    fig.update_yaxes(title_text=axis1_name, secondary_y=False, color='cyan')
    fig.update_yaxes(title_text=axis2_name, secondary_y=True, color='magenta')
    fig.update_yaxes(title_text=axis3_name, secondary_y=True, color='yellow')

    # Show the figure
    return fig


def calculate_rolling_beta_and_correlation(asset_df, benchmark_df, n, price_column='Close'):
    """
    Calculate rolling beta values and rolling correlation for asset compared to a benchmark.

    Parameters:
    - asset_df: DataFrame containing price data for the asset.
    - benchmark_df: DataFrame containing price data for the benchmark.
    - n: The number of data points to use for each calculation (rolling window size).
    - price_column: The name of the column in the DataFrames that contains the price data.

    Returns:
    - A tuple of two Pandas Series: (beta_series, correlation_series), where beta_series contains the beta values
      for each data point based on the previous n data points, and correlation_series contains the correlation values
      for each data point based on the previous n data points.
    """
    
    # Calculate daily returns for both dataframes
    asset_returns = asset_df[price_column].pct_change()
    benchmark_returns = benchmark_df[price_column].pct_change()

    # Initialize lists to store the calculated beta and correlation values
    beta_values = [np.nan] * n  # Start with n NaN values to align with the original DataFrame
    correlation_values = [np.nan] * n  # Start with n NaN values for correlation

    # Loop through the dataset, starting from the n+1 data point
    for i in range(n, len(asset_df)):
        # Select the window of the last n returns for both the asset and the benchmark
        asset_window = asset_returns.iloc[i-n:i]
        benchmark_window = benchmark_returns.iloc[i-n:i]
        
        # Calculate covariance between asset and benchmark returns in the window
        covariance = np.cov(asset_window, benchmark_window)[0, 1]
        
        # Calculate the variance of benchmark returns in the window
        variance = np.var(benchmark_window)
        
        # Calculate beta for the window and append it to the list
        beta = covariance / variance
        beta_values.append(beta)
        
        # Calculate correlation for the window and append it to the list
        correlation = np.corrcoef(asset_window, benchmark_window)[0, 1]
        correlation_values.append(correlation)

    # Create Pandas Series from the lists of beta and correlation values
    beta_series = pd.Series(beta_values, index=asset_df.index)
    correlation_series = pd.Series(correlation_values, index=asset_df.index)
    
    return beta_series, correlation_series

def plot_kline_data(kline_data, title):
    """
    Plots the price data for a single dataset as a candlestick chart.

    Parameters:
    - kline_data: DataFrame containing the price data to plot.
    - title: String, the title of the plot.
    """
    
    fig = go.Figure(data=[go.Candlestick(x=kline_data['Open Time'],
                                         open=kline_data['Open'],
                                         high=kline_data['High'],
                                         low=kline_data['Low'],
                                         close=kline_data['Close'])])

    fig.update_layout(
        title={
            'text': title,
            'font': {
                'color': 'white'  
            }
        },
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white'),
        height=600,
        xaxis_rangeslider_visible=False
    )

    fig.update_xaxes(showgrid=False, showline=True, linewidth=2, linecolor='white', tickfont=dict(color='white'))
    fig.update_yaxes(showgrid=False, showline=True, linewidth=2, linecolor='white', tickfont=dict(color='white'))

    return fig

import pandas as pd
import numpy as np

def calculate_rolling_volatility(asset_df, n, price_column='Close'):
    """
    Calculate rolling volatility for an asset.

    Parameters:
    - asset_df: DataFrame containing price data for the asset.
    - n: The number of data points to use for each volatility calculation (rolling window size).
    - price_column: The name of the column in the DataFrame that contains the price data.

    Returns:
    - A Pandas Series containing the volatility values for each data point based on the previous n data points.
    """
    
    # Calculate daily returns for the asset
    asset_returns = asset_df[price_column].pct_change()
    
    # Calculate rolling volatility using the standard deviation of returns
    # multiplied by the square root of 252 to annualize it
    rolling_volatility = asset_returns.rolling(window=n).std() * np.sqrt(365)
    
    # The rolling function automatically aligns the result with the original DataFrame's index
    return rolling_volatility



# Example usage
# Assuming `asset_df` is your DataFrame with the price data
# rolling_volatility = calculate_rolling_volatility(asset_df, 20)

# ARBETH=get_kline_data_from_binance('ETHUSDT','4h',10000)
# c=1
# plot_kline_data(ARBETH,'ARBETH').show()

# ETHARB=reverse_price(ARBETH)
# ETHUSDC=get_kline_data_from_binance('ETHUSDC','1h',72)

# plot_price_comparison(ETHUSDC,ETHARB,'ETH/USDC','ETH/ARB')


# n = 20  # Rolling window size

# ARBUSD=get_kline_data_from_binance('ARBUSDT','1h',336)
# ETHUSD=get_kline_data_from_binance('ETHUSDC','1h',336)
# ARBETH=get_kline_data_from_binance('ARBETH','1h',336)
# ETHARB=reverse_price(ARBETH)
# beataserie=calculate_rolling_beta(ARBUSD,ETHUSD,n,price_column='average')
# beta_series, correlation_series = calculate_rolling_beta_and_correlation(ARBUSD, ETHUSD, n, 'Close')

# plot_dual_axis_time_series_plotly(ETHUSD['Open Time'],beta_series,ETHARB['average'],label1='Beta',label2='ETH/USDC',axis1_name='Beta',axis2_name='ETH/USDC',title='Rolling Beta vs ETH/USDC')

# fig=plot_dual_axis_time_series_plotly_three(ARBUSD['Open Time'],beta_series,ARBUSD['normalized_average'],ETHUSD['normalized_average'],label1='Beta',label2='ETH/ARB',label3='Correlation',axis1_name='Beta',axis2_name='ETH/ARB',axis3_name='Correlation',title='Rolling Beta vs ETH/ARB vs Correlation')

# fig.show()
# c=1

# from binance.spot import Spot

# client = Spot()
# # from binance.spot import Spot as Client

# # proxies = { 'https': 'https://127.0.0.1:3213', 'http': 'http://127.0.0.1:3213',}

# # client= Client(proxies=proxies)

# # Get server timestamp
# print(client.time())
# # Get klines of BTCUSDT at 1m interval
# print(client.klines("BTCUSDT", "1m"))
# # Get last 10 klines of BNBUSDT at 1h interval
# print(client.klines("BNBUSDT", "1h", limit=10))

# import httpx

# class BinanceClient:
#     def __init__(self, api_key=None, api_secret=None, proxies=None, timeout=30):
#         # self.api_key = api_key
#         # self.api_secret = api_secret
#         self.proxies = proxies
#         self.timeout = timeout
    
#     def query(self, endpoint, params):
#         url = f'https://api.binance.com{endpoint}'
#         with httpx.Client(proxies=self.proxies, timeout=self.timeout) as client:
#             response = client.get(url, params=params)
#             response.raise_for_status()  # Raise an exception for HTTP errors
#             return response.json()

#     def klines(self, symbol: str, interval: str, **kwargs):
#         """Kline/Candlestick Data

#         GET /api/v3/klines

#         https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data

#         Args:
#             symbol (str): the trading pair
#             interval (str): the interval of kline, e.g 1s, 1m, 5m, 1h, 1d, etc.
#         Keyword Args:
#             limit (int, optional): limit the results. Default 500; max 1000.
#             startTime (int, optional): Timestamp in ms to get aggregate trades from INCLUSIVE.
#             endTime (int, optional): Timestamp in ms to get aggregate trades until INCLUSIVE.
#         """
#         self.check_required_parameters([[symbol, "symbol"], [interval, "interval"]])
#         params = {"symbol": symbol, "interval": interval, **kwargs}
#         return self.query("/api/v3/klines", params)
    
#     def check_required_parameters(self, parameters):
#         for param, name in parameters:
#             if param is None:
#                 raise ValueError(f"Parameter {name} is required")

# # Example usage
# client = BinanceClient(timeout=60)

# symbol = "BTCUSDT"
# interval = "1h"
# start_time = 1625097600000  # Example timestamp in milliseconds
# end_time = 1625184000000  # Example timestamp in milliseconds

# # Calling the klines function with startTime and endTime
# try:
#     klines_data = client.klines(symbol=symbol, interval=interval, startTime=start_time, endTime=end_time)
#     print(klines_data)
# except httpx.RequestError as e:
#     print(f"An error occurred: {e}")

# import requests

# def get_binance_time():
#     url = "http://data-api.binance.vision/api/v3/klines?symbol=ETHUSDT&interval=1h&limit=100000"
    
#     try:
#         response = requests.get(url, timeout=60,verify=False)  # Increase timeout if needed
#         response.raise_for_status()  # Raise an exception for HTTP errors
#         data = response.json()  # Parse the JSON response
#         return data
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred: {e}")
#         return None

def get_binance_future(symbol, interval, limit,startTime=None,endTime=None):
    import requests
    url=f"https://testnet.binancefuture.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=60,verify=False)  # Increase timeout if needed
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()  # Parse the JSON response
        return data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_binance_spot(symbol, interval, limit,startTime=None,endTime=None):
    import requests
    url=f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=60,verify=False)  # Increase timeout if needed
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()  # Parse the JSON response
        return data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


# # Fetch Binance time
# binance_time = get_binance_time()
# kline_data = pd.DataFrame(binance_time)
# print(binance_time)

import time

def get_all_kline_data(symbol, interval, startTime, endTime=None):
    all_data = []
    limit = 1000
    spot_client = Client(base_url="http://data-api.binance.vision")
    while True:
        
        kline_data = spot_client.klines(symbol, interval, limit=limit,startTime=startTime,endTime=endTime)
        
        if len(kline_data) == 0:
            break
        
        all_data.extend(kline_data)
        
        # Update the startTime to the time of the last received data point to avoid overlap
        startTime = kline_data[-1][0] + 1  # Increment by 1 to avoid duplicating the last entry
        
        # Break the loop if the number of data points received is less than the limit
        if len(kline_data) < limit:
            break
        
        # Optional: Sleep to avoid hitting the rate limit
        time.sleep(1)
    
    kline_data = pd.DataFrame(all_data)
    kline_data.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
    kline_data['Open Time'] = pd.to_datetime(kline_data['Open Time'], unit='ms')
    kline_data['Close Time'] = pd.to_datetime(kline_data['Close Time'], unit='ms')
    kline_data['Open'] = kline_data['Open'].astype(float)
    kline_data['High'] = kline_data['High'].astype(float)
    kline_data['Low'] = kline_data['Low'].astype(float)
    kline_data['Close'] = kline_data['Close'].astype(float)
    # check if the high is greater than 10% of the average of the open and close, replace the high with the 110% of the average of the open and close
    kline_data['High'] = kline_data.apply(lambda x: x['High'] if x['High'] < 1.05 * (x['Open']+x['Close'])/2 else 1.0 * (x['Open']+x['Close'])/2, axis=1)
    # check if the low is less than 70% of the average of the open and close, replace the low with the 70% of the average of the open and close
    kline_data['Low'] = kline_data.apply(lambda x: x['Low'] if x['Low'] > 0.95 * (x['Open']+x['Close'])/2 else 1 * (x['Open']+x['Close'])/2, axis=1)
    #average price
    kline_data['average']=kline_data[['Open','High','Low','Close']].mean(axis=1)
    kline_data['normalized_close']=kline_data['Close']/kline_data['Close'].iloc[0]
    kline_data['rsi']=calculate_rsi(kline_data, window=14)
    
    return kline_data


def get_all_kline_future(symbol, interval, startTime, endTime=None):
    all_data = []
    limit = 1000
    while True:
        
        kline_data = get_binance_future(symbol, interval, limit,startTime=startTime,endTime=endTime)
        
        if len(kline_data) == 0:
            break
        
        all_data.extend(kline_data)
        
        # Update the startTime to the time of the last received data point to avoid overlap
        startTime = kline_data[-1][0] + 1  # Increment by 1 to avoid duplicating the last entry
        
        # Break the loop if the number of data points received is less than the limit
        if len(kline_data) < limit:
            break
        
        # Optional: Sleep to avoid hitting the rate limit
        time.sleep(1)
    
    kline_data = pd.DataFrame(all_data)
    kline_data.columns = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
    kline_data['Open Time'] = pd.to_datetime(kline_data['Open Time'], unit='ms')
    kline_data['Close Time'] = pd.to_datetime(kline_data['Close Time'], unit='ms')
    kline_data['Open'] = kline_data['Open'].astype(float)
    kline_data['High'] = kline_data['High'].astype(float)
    kline_data['Low'] = kline_data['Low'].astype(float)
    kline_data['Close'] = kline_data['Close'].astype(float)
    # check if the high is greater than 10% of the average of the open and close, replace the high with the 110% of the average of the open and close
    kline_data['High'] = kline_data.apply(lambda x: x['High'] if x['High'] < 1.05 * (x['Open']+x['Close'])/2 else 1.0 * (x['Open']+x['Close'])/2, axis=1)
    # check if the low is less than 70% of the average of the open and close, replace the low with the 70% of the average of the open and close
    kline_data['Low'] = kline_data.apply(lambda x: x['Low'] if x['Low'] > 0.95 * (x['Open']+x['Close'])/2 else 1 * (x['Open']+x['Close'])/2, axis=1)
    #average price
    kline_data['average']=kline_data[['Open','High','Low','Close']].mean(axis=1)
    kline_data['normalized_close']=kline_data['Close']/kline_data['Close'].iloc[0]
    kline_data['rsi']=calculate_rsi(kline_data, window=14)
    
    return kline_data

def calculate_rsi(data, window=14):
    # Calculate the price changes
    delta = data['Close'].diff()
    
    # Separate the gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate the average gains and losses
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    
    # Calculate the Relative Strength (RS)
    rs = avg_gain / avg_loss
    
    # Calculate the RSI
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def binance_spot_future_spread():
    import pandas as pd
    import plotly.express as px

    symbol = "ETHUSDT"
    interval = "1h"
    limit = 1000

    spot_data = get_binance_spot(symbol, interval, limit)
    future_data = get_binance_future(symbol, interval, limit)

    # Convert data to DataFrame
    columns = ["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", 
            "Quote asset volume", "Number of trades", "Taker buy base asset volume", 
            "Taker buy quote asset volume", "Ignore"]

    spot_df = pd.DataFrame(spot_data, columns=columns)
    future_df = pd.DataFrame(future_data, columns=columns)

    # Convert "Open time" to datetime for better handling
    spot_df['Open time'] = pd.to_datetime(spot_df['Open time'], unit='ms')
    future_df['Open time'] = pd.to_datetime(future_df['Open time'], unit='ms')

    # Merge data on "Open time" to ensure they have the same times
    merged_df = pd.merge(spot_df, future_df, on="Open time", suffixes=('_spot', '_future'))

    # Calculate the difference between corresponding open prices
    merged_df['Open Difference Percentage'] = ((merged_df['Open_future'].astype(float) - merged_df['Open_spot'].astype(float)) / merged_df['Open_spot'].astype(float)) * 100

    # Create a figure with two y-axes
    fig = go.Figure()

    # Add spot price trace
    fig.add_trace(
        go.Scatter(
            x=merged_df['Open time'],
            y=merged_df['Open_spot'].astype(float),
            name='Spot Price',
            yaxis='y1'
        )
    )

    # Add percentage difference trace
    fig.add_trace(
        go.Scatter(
            x=merged_df['Open time'],
            y=merged_df['Open Difference Percentage'],
            name='Open Price Difference Percentage (Future - Spot)',
            yaxis='y2'
        )
    )

    # Update layout to include two y-axes
    fig.update_layout(
        title='Spot Price and Open Price Difference Percentage for ETH',
        xaxis_title='Time',
        yaxis=dict(
            title='Spot Price',
            titlefont=dict(
                color='#1f77b4'
            ),
            tickfont=dict(
                color='#1f77b4'
            )
        ),
        yaxis2=dict(
            title='Open Price Difference Percentage',
            titlefont=dict(
                color='#ff7f0e'
            ),
            tickfont=dict(
                color='#ff7f0e'
            ),
            anchor='x',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0)',
            bordercolor='rgba(255,255,255,0)'
        )
    )

    fig.show()



