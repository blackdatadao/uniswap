#!/usr/bin/env python
# -*- coding: utf-8 -*-
#streamlit run pools.py
import asyncio,threading

# Create a new event loop and set it as the current event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

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
import requests,os

from streamlit.components.v1 import iframe
from binance_kline import get_kline_data_from_binance,reverse_price,plot_price_comparison,plot_kline_data,calculate_rolling_beta,plot_dual_axis_time_series_plotly,calculate_rolling_beta_and_correlation,plot_dual_axis_time_series_plotly_three,calculate_rolling_volatility
from subgraph_liquidity_distribution_arb import get_volume_chart,get_pool_distribution,get_hourly_locked_token_chart


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

def dune_embed_url(iframe_url):
    i_width=600
    i_height=400
    iframe(iframe_url, width=i_width, height=i_height, scrolling=True)

def nft_infomration_to_show(nft_list):
    #return data with columns 'nft_id','symbol0','symbol1','tick_lower','tick_upper','fee_usdc','withdrawable_tokens0','withdrawable_tokens1','create_time','create_token0','create_token1','value','duration','current_price'
    nft_data = get_pools_details(nft_list)
    df3=pd.DataFrame(nft_data)
    #create a new column 'symbol1_price',if symbol1 is arb,then symbole1_price is the arbusdc_price,else is the 1
    df3['symbol1_price']=df3['symbol1'].apply(lambda x: arbusdc_price if x=='ARB' else 1)
    #create a new column 'symbol0_price',its value is ethusdc_price
    df3['symbol0_price']=ethusdc_price
    df3['fee_usdc']=df3['current_fee0']*df3['symbol0_price']+df3['current_fee1']*df3['symbol1_price']
    df3['value']=df3['withdrawable_tokens0']*df3['symbol0_price']+df3['withdrawable_tokens1']*df3['symbol1_price']

    df4=df3[['nft_id','symbol0','symbol1','tick_lower','tick_upper','fee_usdc','withdrawable_tokens0','withdrawable_tokens1','create_time','create_token0','create_token1','value','duration','current_price','pool_address']]
    #convert time object of df3['create_time'] to time object with format '%m-%d %H:%M'
    df4['create_time']=df4['create_time'].map(lambda x:datetime.strptime(x,'%Y-%m-%d %H:%M:%S').strftime('%m-%d %H:%M'))
    df4['tick_avg']=(df4['tick_lower']+df4['tick_upper'])/2
    #create new colomn which is fee_usdc/value/duration*24
    df4['apr']=df4['fee_usdc']/df4['value']/df4['duration']*24*100
    df4['return']=df4['fee_usdc']/df4['value']*100
    df4=df4.round(1)
    df4=df4.sort_values(by='nft_id',ascending=True)
    return df4

def get_nft_data(nft_id, w3, factory_contract, nft_position_manager):
    d = my.get_output_by_nft_id(nft_id, w3, factory_contract, nft_position_manager)
    return d

def get_pools_details(nft_list):
    nft_data = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = []
        # for nft_id in df['nft_id']:
        for nft_id in nft_list:
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
    # start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    # print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp).tail(1)
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        # df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:]) if x.startswith('0x') else bytes.fromhex(x)))

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
    # start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    # print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:]) if x.startswith('0x') else bytes.fromhex(x)))

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
    # start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    # print('time cost:',time.time()-start_time)

    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        
        df=pd.read_json(temp)
        timestamp_start=connection.eth.get_block(int(df['blockNumber'][0]))['timestamp']
        timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_start)))
        # print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end)))
        
        
        #get the timestamp of each transaction
        # df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        # df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:]) if x.startswith('0x') else bytes.fromhex(x)))
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
    # start_time=time.time()
    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    # print('time cost:',time.time()-start_time)
    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        df=pd.read_json(temp).iloc[-1,0]
        #get the timestamp of each transaction
        df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        #{"indexed":false,"internalType":"uint128","name":"liquidity","type":"uint128"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"IncreaseLiquidity","type":"event"}
        # df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
        df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:]) if x.startswith('0x') else bytes.fromhex(x)))

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

def send_id_to_server(user_input,nft_list):
    url = 'http://42.192.17.155/realised_id'
    headers = {'Content-Type': 'application/json'}
    if user_input not in nft_list['nft_id'].values:
        st.error(f"ID {user_input} not found.")
        return
    else:
        try:
            # GET request to fetch the current list
            response = requests.get(url)
            if response.status_code == 200:
                    data = response.json()
                    data.append(user_input)
                    # POST request to send the updated list back to the server
                    post_response = requests.post(url, json=data, headers=headers)
                    post_response.raise_for_status()  # Check for HTTP errors
                    
                    # st.session_state.show_success = True

                    success = st.success(f"{user_input} successfully sent to server.")
                    time.sleep(3)
                    success.empty() # Clear the alert
            else:
                st.error('Error:', response.status_code)
        except json.JSONDecodeError:
            st.error('Error: Invalid JSON')
        except requests.exceptions.HTTPError as e:
            st.error('HTTP error occurred:', e)
        except requests.exceptions.RequestException as e:
            st.error('Request failed:', e)
def show_realised_id():
    url = 'http://42.192.17.155/realised_id'
    headers = {'Content-Type': 'application/json'}
    try:
        # GET request to fetch the current list
        response = requests.get(url)
        if response.status_code == 200:
                data = response.json()
                df_realised=nft_infomration_to_show(data)
                for index,row in df_realised.iterrows():
                    with st.container():
                        color = "green" if row['tick_lower'] < row['current_price'] and row['tick_upper'] > row['current_price'] else "black"
                        st.markdown(f'<span style="color: {color};"><strong>{row["symbol0"]}/{row["symbol1"]} < {row["tick_lower"]}-{row["tick_upper"]}></strong>@{row["tick_avg"]}  |  **Create:** {row["create_token0"]}/{row["create_token1"]} @{row["create_time"]}|{row["duration"]}H **#** {row["nft_id"]}</span>', unsafe_allow_html=True)
                        st.markdown(f'<span style="color: {color};"><strong>**Fee** {row["fee_usdc"]}</strong> < {row["withdrawable_tokens0"]}|{row["withdrawable_tokens1"]}> **value** {row["value"]} | {row["return"]} % **day** {row["apr"]} %</span>', unsafe_allow_html=True)
        else:
            st.error('Error:', response.status_code)
    except json.JSONDecodeError:
        st.error('Error: Invalid JSON')
    except requests.exceptions.HTTPError as e:
        st.error('HTTP error occurred:', e)
    except requests.exceptions.RequestException as e:
        st.error('Request failed:', e)

def delete_id_from_server(user_input):
    url = 'http://42.192.17.155/realised_id'
    headers = {'Content-Type': 'application/json'}
    try:
        # GET request to fetch the current list
        response = requests.get(url)
        if response.status_code == 200:
                data = response.json()
                if user_input in data:
                    data.remove(user_input)
                    # POST request to send the updated list back to the server
                    post_response = requests.post(url, json=data, headers=headers)
                    post_response.raise_for_status()  # Check for HTTP errors
                    success = st.success(f"{user_input} successfully deleted.")
                    time.sleep(3)
                    success.empty() # Clear the alert
                else:
                    st.error(f"delete ID {user_input} not found.")
                    return

                
                # st.session_state.show_success = True

        else:
            st.error('Error:', response.status_code)
    except json.JSONDecodeError:
        st.error('Error: Invalid JSON')
    except requests.exceptions.HTTPError as e:
        st.error('HTTP error occurred:', e)
    except requests.exceptions.RequestException as e:
        st.error('Request failed:', e)
    
# def check_and_alert(df, to_email):
#     for index, row in df.iterrows():
#         current_price = my.get_current_price_by_pool_address(w3,row['pool_address'],1)['price0']
#         if current_price < row['tick_lower'] or current_price > row['tick_upper']:
#             subject = f"Price Alert for NFT ID {row['nft_id']}"
#             body = f"The current price {current_price} has exceeded the tick range for NFT ID {row['nft_id']}.\n\nDetails:\n{row}"
#             time.sleep(3)
#             send_email(subject, body, to_email)


# Initialize previous_prices with default values
def initialize_previous_prices(df):
    global previous_prices
    previous_prices = {}
    for index, row in df.iterrows():
        previous_prices[row['nft_id']]= my.get_current_price_by_pool_address(w3,row['pool_address'],1)['price0']


def check_and_alert(df, to_email):
    global previous_prices
    sent=False
    for index, row in df.iterrows():
        body=[]
        nft_id = row['nft_id']
        current_price = my.get_current_price_by_pool_address(w3,row['pool_address'],1)['price0']
        if nft_id in previous_prices:
            prev_price = previous_prices[nft_id]
            if (prev_price < row['tick_lower'] and current_price >= row['tick_lower']) or \
                   (prev_price > row['tick_upper'] and current_price <= row['tick_upper']) or\
                (prev_price > row['tick_lower'] and current_price <= row['tick_lower']) or \
                   (prev_price < row['tick_upper'] and current_price >= row['tick_upper']):
                    subject = f"Price Alert {current_price}"
                    body =body.append(f"\nThe current price {current_price} has crossed NFT ID {nft_id}.\n\nDetails:\n{row}")
                    sent=True
        previous_prices[nft_id] = current_price
    if sent==True:
        send_email(subject, body, to_email)
        sent=False
    else:
        send_email('no alert', 'no alert', to_email)

def fetch_and_check_periodically(nft_data, to_email):
    global monitoring
    monitoring = True
        # nft_data = nft_infomration_to_show(nft_list)
    initialize_previous_prices(nft_data)
    while monitoring:
        check_and_alert(nft_data, to_email)
        print('checked once time')
        time.sleep(30)
        # st.experimental_rerun()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

def send_email(subject, body, to_email):


    from_email = "chainredking@gmail.com"
    password = "yciowpetippvhomh"

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Replace with your SMTP server and port
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email sent successfully")
        # st.success("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
        send_email(subject, body, to_email)
        # st.error(f"Failed to send email: {e}")

def initialize_web3():
    global w3, nft_position_manager, factory_contract
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





# html_content = f"""
# <div style="display: flex; justify-content: space-between;background-color: #f0f2f6; padding: 10px; border-radius: 5px;font-size: 18px;">
#     <div style="margin-right: 10px;"><strong>ETH/usdc:</strong> {round(ethusdc_price,2)}</div>
#     <div style="margin-right: 10px;"><strong>ETH/arb:</strong> {round(arbeth_price,2)}</div>
#     <div><strong>ARB/usdc:</strong> {round(arbusdc_price,3)}</div>
# </div>
# """


#save the open nft to a csv file
# df_open_nft.to_csv('open_nft.csv',index=False)
# # read the open nft from a csv file
# df_open_nft=pd.read_csv('open_nft.csv')



def main():
    global monitoring,ethusdc_price, arbeth_price, arbusdc_price
    monitoring = False
    initialize_web3()

    # to_email = st.text_input("Enter your email for alerts")
    to_email='34916514@qq.com'

    url='http://42.192.17.155/nft_list'
    response = requests.get(url)
    assert response.status_code==200
    nfts_list=response.json()
    nft_list=pd.DataFrame(nfts_list)

    ethusdc_price=my.get_current_price_by_pool_address(w3,'0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443',1)['price0']
    arbeth_price=my.get_current_price_by_pool_address(w3,'0xc6f780497a95e246eb9449f5e4770916dcd6396a',1)['price0']
    arbusdc_price=1/arbeth_price*ethusdc_price
    #select the nfts which is open from the nft_list 
    df=nft_list[nft_list['closed']=='open'][0:]#delete a unnormal one

    df_open_nft=nft_infomration_to_show(df['nft_id'])
    fetch_and_check_periodically(df_open_nft, to_email)


main()
