#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import pandas as pd
import json,time
from web3 import Web3,HTTPProvider
import function as my
from datetime import datetime
import streamlit as st
import concurrent.futures

from eth_abi import decode
import numpy as np
import plotly.express as px
import requests

from streamlit.components.v1 import iframe
from binance_kline import get_kline_data_from_binance,reverse_price,plot_price_comparison,plot_kline_data,calculate_rolling_beta,plot_dual_axis_time_series_plotly,calculate_rolling_beta_and_correlation,plot_dual_axis_time_series_plotly_three,calculate_rolling_volatility
from subgraph_liquidity_distribution_arb import get_volume_chart,get_pool_distribution


import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

factory_address='0x1F98431c8aD98523631AE4a59f267346ea31F984'
contract_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
provider_arb='https://arb1.arbitrum.io/rpc'
provider_arb_2='https://arbitrum-mainnet.infura.io/v3/02040948aa024dc49e8730607e0caece'

w3=Web3(HTTPProvider(provider_arb_2, {'timeout': 20}))

with open(r"arbitrum nft position manager v3 ABI.json") as json_file:
        contract_abi = json.load(json_file)
nft_position_manager=w3.eth.contract(
    address=Web3.to_checksum_address(contract_address.lower()),abi=contract_abi)

with open(r"factory abi.json") as json_file:
        factory_abi = json.load(json_file)
factory_contract=w3.eth.contract(address=Web3.to_checksum_address(factory_address.lower()),abi=factory_abi)
wallet_address='0x9742499f4f1464c5b3dbf4d04adcbc977fbf7baa'

ethusdc_price=my.get_current_price_by_pool_address(w3,'0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443',1)['price0']
arbeth_price=my.get_current_price_by_pool_address(w3,'0xc6f780497a95e246eb9449f5e4770916dcd6396a',1)['price0']
arbusdc_price=1/arbeth_price*ethusdc_price

st.markdown(f'**ETH/usdc** {round(ethusdc_price,2)}')
st.markdown(f'**ETH/arb** {round(arbeth_price,2)}')

try:
    my.update_nft_list(wallet_address,w3,nft_position_manager)
except:
    print('error,retry...')
    my.update_nft_list(wallet_address,w3,nft_position_manager)
print('update nft_list finished,wallet address ',wallet_address)

url='http://42.192.17.155/nft_list'
response = requests.get(url)
assert response.status_code==200
nfts_list=response.json()
nft_list=pd.DataFrame(nfts_list)
#select the nfts which is open from the nft_list 
df=nft_list[nft_list['closed']=='open'][0:]#delete a unnormal one


def get_nft_data(nft_id, w3, factory_contract, nft_position_manager):
    d = my.get_output_by_nft_id(nft_id, w3, factory_contract, nft_position_manager)
    return d

def get_pools_details(df):
    nft_data = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = []
        for nft_id in df['nft_id']:
            future = executor.submit(get_nft_data, nft_id, w3, factory_contract, nft_position_manager)
            results.append(future)
    
        for result in concurrent.futures.as_completed(results):
            nft_data.append(result.result())
    
    return nft_data

def get_current_price_etharb(
        connection
    ):
    # fb=74711249,tb=74811249
    fb=connection.eth.block_number-100
    tb=connection.eth.block_number
    cAddress="0xc6f780497a95e246eb9449f5e4770916dcd6396a"
    tp=["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"]
    start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp).tail(1)
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['sqrtPrice']=df['data_decoded'].map(lambda x:x[2])
        df['amount0']=abs(df['data_decoded'].map(lambda x:x[0]))
        df['amount1']=abs(df['data_decoded'].map(lambda x:x[1]))

        # df['tick']=df['data_decoded'].map(lambda x:x[3])
        decimals1=18
        decimals0=18 #ETH
        price0 = df['amount1']/10**decimals1/(df['amount0']/10**decimals0)
        # Calculate the price of token0 in terms of token1
        price1 = 1 / price0
        # return the value of price0

        return dict(
           price0=price0.values[0])
    else:
        raise Exception('fetched None')

def get_history_price_etharb(
        connection
    ):
    # fb=74711249,tb=74811249
    minutes=240
    fb=connection.eth.block_number-3*60*minutes
    tb=connection.eth.block_number
    cAddress="0xc6f780497a95e246eb9449f5e4770916dcd6396a"
    tp=["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"]
    start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['sqrtPrice']=df['data_decoded'].map(lambda x:x[2])
        
        df['amount0']=abs(df['data_decoded'].map(lambda x:x[0]))
        df['amount1']=abs(df['data_decoded'].map(lambda x:x[1]))
        df=df[(df['amount0']!=0)&(df['amount1']!=0)]
        
        # df['tick']=df['data_decoded'].map(lambda x:x[3])
        decimals1=18
        decimals0=18 #ETH
        df['price0'] = df['amount1']/10**decimals1/(df['amount0']/10**decimals0)
        # Calculate the price of token0 in terms of token1
        # price1 = 1 / price0
        # return the value of price0

        return df[['blockNumber','price0']]
    else:
        raise Exception('fetched None')
        
def get_history_price_ethusdc(
        connection
    ):
    # fb=74711249,tb=74811249
    minutes=240
    fb=connection.eth.block_number-3*60*minutes
    tb=connection.eth.block_number
    cAddress="0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443"
    tp=["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"]
    start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['sqrtPrice']=df['data_decoded'].map(lambda x:x[2])
        
        df['amount0']=abs(df['data_decoded'].map(lambda x:x[0]))
        df['amount1']=abs(df['data_decoded'].map(lambda x:x[1]))
        df=df[(df['amount0']!=0)&(df['amount1']!=0)]
        
        # df['tick']=df['data_decoded'].map(lambda x:x[3])
        decimals1=6
        decimals0=18 #ETH
        df['price0'] = df['amount1']/10**decimals1/(df['amount0']/10**decimals0)
        # Calculate the price of token0 in terms of token1
        # price1 = 1 / price0
        # return the value of price0

        return df[['blockNumber','price0']]
    else:
        raise Exception('fetched None')
        
def get_swap_price_ethusdc(
        connection
    ):
    #topic:increase liquidity
    # fb=74711249,tb=74811249
    fb=connection.eth.block_number-10000
    tb=connection.eth.block_number
    cAddress="0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443"
    tp=["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"]
    start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    print('time cost:',time.time()-start_time)
    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        df=pd.read_json(temp).iloc[-1,0]
        #get the timestamp of each transaction
        df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        #{"indexed":false,"internalType":"uint128","name":"liquidity","type":"uint128"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"IncreaseLiquidity","type":"event"}
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['sqrtPrice']=df['data_decoded'].map(lambda x:x[2])
        df['amount0']=abs(df['data_decoded'].map(lambda x:x[0]))
        df['amount1']=abs(df['data_decoded'].map(lambda x:x[1]))
        # df['tick']=df['data_decoded'].map(lambda x:x[3])
        decimals1=6
        decimals0=18 #ETH
        price0 = df['amount1']/10**decimals1/(df['amount0']/10**decimals0)
        # Calculate the price of token0 in terms of token1
        # price1 = 1 / price0

        return dict(
        #    price1=price1,
           price0=price0)
    else:
        raise Exception('fetched None')

def get_summary(df):
    df_balance=df.groupby(['symbol0','symbol1'])[['withdrawable_tokens0','withdrawable_tokens1']].sum()
    df_create=df.groupby(['symbol0','symbol1'])[['create_token0','create_token1']].sum()
    df_fee=df.groupby(['symbol0','symbol1'])[['fee_usdc']].sum()
    df_value=df.groupby(['symbol0','symbol1'])[['value']].sum()
    #combine df_balance,df_create,df_fee,df_value
    df_summary=pd.concat([df_balance,df_create,df_fee,df_value],axis=1)
    df_summary['token0_delta']=df_summary['withdrawable_tokens0']-df_summary['create_token0']
    df_summary['token1_delta']=df_summary['withdrawable_tokens1']-df_summary['create_token1']
    df_summary['average_cost']=df_summary['token1_delta']/df_summary['token0_delta']
    df_summary=df_summary.applymap(lambda x:round(x,1) if isinstance(x,float) else x)
    df_summary.columns=['w0','w1','c0','c1','fee','value','delta0','delta1','cost']
    return df_summary

# summary tabel 
nft_data = get_pools_details(df)
df3=pd.DataFrame(nft_data)
#create a new column 'symbol1_price',if symbol1 is arb,then symbole1_price is the arbusdc_price,else is the 1
df3['symbol1_price']=df3['symbol1'].apply(lambda x: arbusdc_price if x=='ARB' else 1)
#create a new column 'symbol0_price',its value is ethusdc_price
df3['symbol0_price']=ethusdc_price
df3['fee_usdc']=df3['current_fee0']*df3['symbol0_price']+df3['current_fee1']*df3['symbol1_price']
df3['value']=df3['withdrawable_tokens0']*df3['symbol0_price']+df3['withdrawable_tokens1']*df3['symbol1_price']

df4=df3[['nft_id','symbol0','symbol1','tick_lower','tick_upper','fee_usdc','withdrawable_tokens0','withdrawable_tokens1','create_time','create_token0','create_token1','value','duration','current_price']]
#convert time object of df3['create_time'] to time object with format '%m-%d %H:%M'
df4['create_time']=df4['create_time'].map(lambda x:datetime.strptime(x,'%Y-%m-%d %H:%M:%S').strftime('%m-%d %H:%M'))
df4['tick_avg']=(df4['tick_lower']+df4['tick_upper'])/2
#create new colomn which is fee_usdc/value/duration*24
df4['apr']=df4['fee_usdc']/df4['value']/df4['duration']*24*100
df4['return']=df4['fee_usdc']/df4['value']*100
df4=df4.round(1)
df4=df4.sort_values(by='nft_id',ascending=True)
#select the data from df4 where current price in range of tick_lower and tick_upper
df_inrange=df4[(df4['current_price']>=df4['tick_lower'])&(df4['current_price']<=df4['tick_upper'])]
# select the data from df4 where current price is not in range of tick_lower and tick_upper
df_outrange=df4[(df4['current_price']<df4['tick_lower'])|(df4['current_price']>df4['tick_upper'])]
summary_inrange=get_summary(df_inrange)
summary_outrange=get_summary(df_outrange)
summary=get_summary(df4)

st.markdown('total summary')
st.dataframe(summary.round(1))
st.markdown('total summary inrange')
st.dataframe(summary_inrange)
st.markdown('total summary outrange')
st.dataframe(summary_outrange)
for index,row in df4.iterrows():
    with st.container():
        color = "green" if row['tick_lower'] < row['current_price'] and row['tick_upper'] > row['current_price'] else "black"
        st.markdown(f'<span style="color: {color};"><strong>{row["symbol0"]}/{row["symbol1"]} < {row["tick_lower"]}-{row["tick_upper"]}></strong>@{row["tick_avg"]}  |  **Create:** {row["create_token0"]}/{row["create_token1"]} @{row["create_time"]}|{row["duration"]}H **#** {row["nft_id"]}</span>', unsafe_allow_html=True)
        st.markdown(f'<span style="color: {color};"><strong>**Fee** {row["fee_usdc"]}</strong> < {row["withdrawable_tokens0"]}|{row["withdrawable_tokens1"]}> **value** {row["value"]} | {row["return"]} % **day** {row["apr"]} %</span>', unsafe_allow_html=True)


#plot the history price of etharb and ethusdc
df=get_history_price_etharb(w3)
timestamp_start=w3.eth.get_block(int(df['blockNumber'][0]))['timestamp']
timestamp_end=w3.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
tick_values = np.linspace(df["blockNumber"].min(), df["blockNumber"].max(), 4).round()
tick_values_int=[w3.eth.get_block(int(x))['timestamp'] for x in tick_values]
tick_labels = [time.strftime("%d %H:%M",time.localtime(x)) for x in tick_values_int]
y_min = df["price0"].mean() - 5 * df["price0"].std()
y_max = df["price0"].mean() + 5 * df["price0"].std()
price_median = df["price0"].median()
df["price0"] = df["price0"].apply(lambda x: price_median if x < y_min or x > y_max else x)
fig=px.line(df,x='blockNumber',y='price0',title=' end time: '+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
fig.update_xaxes(tickmode='array',tickvals=tick_values, ticktext=tick_labels)
fig.update_layout(title='ETH/arb price')
st.plotly_chart(fig, use_container_width=True
                )

df=get_history_price_ethusdc(w3)
timestamp_start=w3.eth.get_block(int(df['blockNumber'][0]))['timestamp']
timestamp_end=w3.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
tick_values = np.linspace(df["blockNumber"].min(), df["blockNumber"].max(), 4).round()
tick_values_int=[w3.eth.get_block(int(x))['timestamp'] for x in tick_values]
tick_labels = [time.strftime("%d %H:%M",time.localtime(x)) for x in tick_values_int]
y_min = df["price0"].mean() - 5 * df["price0"].std()
y_max = df["price0"].mean() + 5 * df["price0"].std()
price_median = df["price0"].median()
df["price0"] = df["price0"].apply(lambda x: price_median if x < y_min or x > y_max else x)
fig=px.line(df,x='blockNumber',y='price0',title=' end time: '+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
fig.update_xaxes(tickmode='array',tickvals=tick_values, ticktext=tick_labels)
fig.update_layout(title='ETH/usdc price')
st.plotly_chart(fig, use_container_width=True)

#plot 1 hours klines of arbeth
ARBETH=get_kline_data_from_binance('ARBETH','1h',24)
ETHARB=reverse_price(ARBETH)
fig=plot_kline_data(ETHARB,'ETH/ARB 1h klines')
st.plotly_chart(fig, use_container_width=True)

#plot 4 hours klines of arbeth
ARBETH=get_kline_data_from_binance('ARBETH','4h',24)
ETHARB=reverse_price(ARBETH)
fig=plot_kline_data(ETHARB,'ETH/ARB 4h klines')
st.plotly_chart(fig, use_container_width=True)

# plot 1 hours ETH/USD klines
ETHUSD=get_kline_data_from_binance('ETHUSDT','1h',24)
fig=plot_kline_data(ETHUSD,'ETH/USDT 1h klines')
st.plotly_chart(fig, use_container_width=True)

# plot 4 hours ETH/USD klines
ETHUSD=get_kline_data_from_binance('ETHUSDT','4h',24)
fig=plot_kline_data(ETHUSD,'ETH/USDT 4h klines')
st.plotly_chart(fig, use_container_width=True)

# compare 1 hours ETH/USD and ETH/ARB klines with n hours
n=100
ETHARB=reverse_price(get_kline_data_from_binance('ARBETH','1h',n))
ETHUSD=get_kline_data_from_binance('ETHUSDT','1h',n)
fig=plot_price_comparison(ETHUSD,ETHARB,'ETH/USDT','ETH/ARB')
st.plotly_chart(fig, use_container_width=True)

# beta analysis
n = 24  # Rolling window size
m=336
ARBUSD=get_kline_data_from_binance('ARBUSDT','1h',m)
ETHUSD=get_kline_data_from_binance('ETHUSDC','1h',m)
ARBETH=get_kline_data_from_binance('ARBETH','1h',m)
ETHARB=reverse_price(ARBETH)
beataserie=calculate_rolling_beta(ARBUSD,ETHUSD,n,price_column='average')
beta_series, correlation_series = calculate_rolling_beta_and_correlation(ARBUSD, ETHUSD, n, 'Close')
volatility_series_ETH=calculate_rolling_volatility(ETHUSD,n)
volatility_series_ARB=calculate_rolling_volatility(ARBUSD,n)

# fig=plot_dual_axis_time_series_plotly(ETHUSD['Open Time'],beta_series,ETHARB['average'],label1='Beta',label2='ETH/ARB',axis1_name='Beta',axis2_name='ETH/ARB',title='Rolling Beta vs ETH/ARB')
# st.plotly_chart(fig, use_container_width=True)

# fig=plot_dual_axis_time_series_plotly(ETHUSD['Open Time'],beta_series,ETHUSD['average'],label1='Beta',label2='ETH/USD',axis1_name='Beta',axis2_name='ETH/USD',title='Rolling Beta vs ETH/USD')
# st.plotly_chart(fig, use_container_width=True)

fig=plot_dual_axis_time_series_plotly_three(ARBUSD['Open Time'],beta_series,ARBUSD['normalized_average'],ETHUSD['normalized_average'],label1='Beta',label2='ETH/ARB',label3='ETH/USD',axis1_name='Beta',axis2_name='ARB/USD',axis3_name='ETH/USD',title='Rolling Beta vs ETH/ARB vs ETH/USD')
st.plotly_chart(fig, use_container_width=True)

fig=plot_dual_axis_time_series_plotly_three(ARBUSD['Open Time'],correlation_series,ARBUSD['normalized_average'],ETHUSD['normalized_average'],label1='corelation',label2='ETH/ARB',label3='ETH/USD',axis1_name='Corelation',axis2_name='ARB/USD',axis3_name='ETH/USD',title='corelation vs ARB/USD vs ETH/USD')
st.plotly_chart(fig, use_container_width=True)

fig=plot_dual_axis_time_series_plotly_three(ARBUSD['Open Time'],ETHUSD['normalized_average'],volatility_series_ETH,volatility_series_ARB,label1='ETH/USD',label2='ETH vol',label3='ARB vol',axis1_name='ETH/USD',axis2_name='ETH vol',axis3_name='ARB vol',title='volatility vs ARB/USD vs ETH/USD')
st.plotly_chart(fig, use_container_width=True)

fig=get_volume_chart()
st.plotly_chart(fig, use_container_width=True)

total_amount0_,total_amount1_,current_price,fig_left,fig_right=get_pool_distribution()
st.markdown(f'**total amount0** {total_amount0_}')
st.markdown(f'**total amount1** {total_amount1_}')
st.markdown(f'**current price** {current_price}')
st.plotly_chart(fig_left, use_container_width=True)
st.plotly_chart(fig_right, use_container_width=True)

iframe_url='https://dune.com/embeds/2272843/3725900'
i_width=600
i_height=400
iframe(iframe_url, width=i_width, height=i_height, scrolling=True)

url_table_arb_price_vol='https://dune.com/embeds/2272843/3725430'
url_usd_vol='https://dune.com/embeds/2349162/3846118'
url_op_price_vol='https://dune.com/embeds/2331467/3816872'

iframe(url_usd_vol, width=i_width, height=i_height, scrolling=True)
iframe(url_op_price_vol, width=i_width, height=i_height, scrolling=True)
iframe(url_table_arb_price_vol, width=i_width, height=i_height, scrolling=True)


url="https://info.uniswap.org/#/arbitrum/"
st.markdown(f"[official data]({url})")

