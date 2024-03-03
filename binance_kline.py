# !/usr/bin/env python

import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    # check if the high is greater than 10% of the average of the open and close, replace the high with the 110% of the average of the open and close
    kline_data['High'] = kline_data.apply(lambda x: x['High'] if x['High'] < 1.05 * (x['Open']+x['Close'])/2 else 1.05 * (x['Open']+x['Close'])/2, axis=1)
    # check if the low is less than 70% of the average of the open and close, replace the low with the 70% of the average of the open and close
    kline_data['Low'] = kline_data.apply(lambda x: x['Low'] if x['Low'] > 0.95 * (x['Open']+x['Close'])/2 else 0.95 * (x['Open']+x['Close'])/2, axis=1)
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
        legend=dict(orientation="h", xanchor="center", yanchor="bottom", x=0.5, y=-0.8, font=dict(size=24, color="white"))
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
        legend=dict(font=dict(size=18, color="white"))

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
        legend=dict(font=dict(size=18, color="white"))
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
        font=dict(color='white')
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

# ARBETH=get_kline_data_from_binance('ETHUSDT','1h',72)
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
c=1

# from binance.spot import Spot

# client = Spot()

# # Get server timestamp
# print(client.time())
# # Get klines of BTCUSDT at 1m interval
# print(client.klines("BTCUSDT", "1m"))
# # Get last 10 klines of BNBUSDT at 1h interval
# print(client.klines("BNBUSDT", "1h", limit=10))