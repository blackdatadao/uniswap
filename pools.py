#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import pandas as pd
import json
from web3 import Web3,HTTPProvider
import function as my
from datetime import datetime
import streamlit as st
import concurrent.futures

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

with open('nfts_list.json') as f:
     nfts_list=json.load(f)

nft_list=pd.DataFrame(nfts_list)


#select the nfts which is open from the nft_list 
df=nft_list[nft_list['closed']=='open'][1:]#delete a unnormal one

nft_data = []

def get_nft_data(nft_id, w3, factory_contract, nft_position_manager):
    d = my.get_output_by_nft_id(nft_id, w3, factory_contract, nft_position_manager)
    return d

def main():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = []
        for nft_id in df['nft_id']:
            future = executor.submit(get_nft_data, nft_id, w3, factory_contract, nft_position_manager)
            results.append(future)
    
        for result in concurrent.futures.as_completed(results):
            nft_data.append(result.result())
    
    return nft_data

nft_data = main()

df3=pd.DataFrame(nft_data)
#create a new column 'symbol1_price',if symbol1 is arb,then symbole1_price is the arbusdc_price,else is the 1
df3['symbol1_price']=df3['symbol1'].apply(lambda x: arbusdc_price if x=='ARB' else 1)
#create a new column 'symbol0_price',its value is ethusdc_price
df3['symbol0_price']=ethusdc_price
df3['fee_usdc']=df3['current_fee0']*df3['symbol0_price']+df3['current_fee1']*df3['symbol1_price']
df3['value']=df3['withdrawable_tokens0']*df3['symbol0_price']+df3['withdrawable_tokens1']*df3['symbol1_price']
df4=df3[['nft_id','symbol0','symbol1','tick_lower','tick_upper','fee_usdc','withdrawable_tokens0','withdrawable_tokens1','create_time','create_token0','create_token1','value','duration']]
#convert time object of df3['create_time'] to time object with format '%m-%d %H:%M'
df4['create_time']=df4['create_time'].map(lambda x:datetime.strptime(x,'%Y-%m-%d %H:%M:%S').strftime('%m-%d %H:%M'))
df4['tick_avg']=(df4['tick_lower']+df4['tick_upper'])/2
#create new colomn which is fee_usdc/value/duration*24
df4['apr']=df4['fee_usdc']/df4['value']/df4['duration']*24*100
df4=df4.round(1)
df4=df4.sort_values(by='nft_id',ascending=True)
for index,row in df4.iterrows():
    with st.container():
        st.markdown('**ID** '+str(row['nft_id'])+'  '+row['symbol0']+'/'+row['symbol1']+'<'+str(row['tick_lower'])+'-'+str(row['tick_upper'])+'>'+'<'+str(row['tick_avg'])+'>'+' **Duration:** '+str(row['duration'])+'mins'+' '+row['create_time'])    
        st.markdown('**Token0:** '+str(row['create_token0'])+' **Token1:** '+str(row['create_token1'])+' **Withdrawable0:** '+str(row['withdrawable_tokens0'])+' **Withdrawable1:** '+str(row['withdrawable_tokens1'])+' **Fee:** '+str(row['fee_usdc'])+' **Value:** '+str(row['value'])+' **APR:** '+str(row['apr'])+'%')  
#         st.write('---')

# st.table(df4)
