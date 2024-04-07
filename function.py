#!/usr/bin/env python
# -*- coding: utf-8 -*-
#streamlit run pools.py --server.address=0.0.0.0


from math import log
from web3 import Web3,HTTPProvider
import time,json
from eth_abi import decode
import pandas as pd 
from flowint import UFlow
import numpy as np
from datetime import datetime
import requests
# import streamlit as st

#all nfts with same contract address. nft position manager and nft pools are differnt contracts
#nft position manager contract address:0xC36442b4a4522E871399CD717aBDD847Ab11FE88
# factory contract address:0x1F98431c8aD98523631AE4a59f267346ea31F984
#nft pools contract address for differnt pools:0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443 weth/usdc 
#0xc6f780497a95e246eb9449f5e4770916dcd6396a weth/arb
# a nft_id example:NFT_ID=548111
#mint event is from nft pools contract and increase liquidity is from nft position manager contract
# generate a function to get collected fees of a uniswap pool by nft_id

#create a function to convert uniswap v3 tick to price

def timestamp_to_time(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp))



    

def tick_to_price(tick,decimals_token0,decimals_token1):
    """convert uniswap v3 tick to price 1 token1=price token0"""
    price0=1.0001**tick
    price=price0*10**(decimals_token0-decimals_token1)
    return price

#create a function to revert function tick_to_price,given price,return tick
def price_to_tick(price,decimals_token0,decimals_token1):
    price0=(price)/10**(decimals_token0-decimals_token1)
    tick=int(round(log(price0,1.0001),0))
    return tick

#create a funtion to get symbol of token by token address
def get_symbol_by_address(address,w3):
    symbol_abi={
        'constant': True,
        'inputs': [],
        'name': 'symbol',
        'outputs': [{'name': '', 'type': 'string'}],
        'payable': False,
        'stateMutability': 'view',
        'type': 'function',
    }
    token=w3.eth.contract(address=address,abi=[symbol_abi])
    symbol=token.functions.symbol().call()
    return symbol
#create a funtion to get decimals of token by token address
def get_decimals_by_address(address,w3):
    decimals_abi={
        'constant': True,
        'inputs': [],
        'name': 'decimals',
        'outputs': [{'name': '', 'type': 'uint8'}],
        'payable': False,
        'stateMutability': 'view',
        'type': 'function',
    }
    token=w3.eth.contract(address=address,abi=[decimals_abi])
    decimals=token.functions.decimals().call()
    return decimals

def get_pool_infor_by_nft_id(nft_id,nft_position_manager):
    # with open(r"D:\app\uniswap_bot\arbitrum nft position manager v3 ABI.json") as json_file:
    #     contract_abi = json.load(json_file)
    # contract_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
    # nft_position_manager=w3.eth.contract(address=contract_address,abi=contract_abi)
    position_data=nft_position_manager.functions.positions(nft_id).call()
    pool_address=position_data[1]
    fee=position_data[4]
    range1=position_data[5]
    range2=position_data[6]
    token0=position_data[2]
    token1=position_data[3]
    liquidity=position_data[7]
    return {'nft_id_0':nft_id,'fee':fee,'token0':token0,'token1':token1,'range1':range1,'range2':range2,'liquidity':liquidity}

def get_NFTS_by_address(address,w3):
    with open(r"D:\app\uniswap_bot\arbitrum nft position manager v3 ABI.json") as json_file:
        contract_abi = json.load(json_file)
    contract_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
    nft_position_manager=w3.eth.contract(address=contract_address,abi=contract_abi)
    nft_balance=nft_position_manager.functions.balanceOf(Web3.to_checksum_address(address.lower())).call()
    index=0
    NFTS=[]
    while index<nft_balance:
        nft_id=nft_position_manager.functions.tokenOfOwnerByIndex(Web3.to_checksum_address(address.lower()),index).call()
        liquidity=get_pool_infor_by_nft_id(nft_id,nft_position_manager)['liquidity']
        if liquidity>0:
            closed='open'
        else:
            closed='closed'
        NFTS.append(dict(nft_id=nft_id,index=index,closed=closed))
        index+=1
        print(index,'...finished')
        #save NFTS to a json file
        with open (r'D:\app\uniswap_bot\NFTS.json','w') as f:
            json.dump(NFTS,f)
    return NFTS

def get_new_NFTS_by_address(address,w3,nft_position_manager,last_index):
    # with open(r"D:\app\uniswap_bot\arbitrum nft position manager v3 ABI.json") as json_file:
    #     contract_abi = json.load(json_file)
    # contract_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
    # nft_position_manager=w3.eth.contract(address=contract_address,abi=contract_abi)
    nft_balance=nft_position_manager.functions.balanceOf(Web3.to_checksum_address(address.lower())).call()
    index=last_index+1
    NFTS=[]
    while index<nft_balance:
        nft_id=nft_position_manager.functions.tokenOfOwnerByIndex(Web3.to_checksum_address(address.lower()),index).call()
        liquidity=get_pool_infor_by_nft_id(nft_id,nft_position_manager)['liquidity']
        if liquidity>0:
            closed='open'
        else:
            closed='closed'
        NFTS.append(dict(nft_id=nft_id,index=index,closed=closed))
        print(index,'...finished')
        index+=1
        #save NFTS to a json file
        with open (r'D:\app\uniswap_bot\new_NFTS.json','w') as f:
            json.dump(NFTS,f)
    return NFTS


def get_increase_liquidity_by_nft_id(
        connection,
        nft_id):
    #topic:increase liquidity
    # fb=74711249,tb=74811249
    fb=0
    tb=connection.eth.block_number
    cAddress="0xc36442b4a4522e871399cd717abdd847ab11fe88"
    tp=["0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f",'0x'+hex(nft_id)[2:].rjust(64,'0')]
    # tp=["0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f"]

    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        df=pd.read_json(temp)
        #get the timestamp of each transaction
        df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        df['data_decoded'] = df['data'].map(
            lambda x: decode(
                ['uint256', 'uint256', 'uint256'],
                bytes.fromhex(x[2:] if x.startswith('0x') else x)
            )
        )
        #{"indexed":false,"internalType":"uint128","name":"liquidity","type":"uint128"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"IncreaseLiquidity","type":"event"}
        # df['data_decoded']=df['data'].map(lambda x:decode(['uint256','uint256','uint256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['token0']=df['data_decoded'].map(lambda x:x[1])
        df['token1']=df['data_decoded'].map(lambda x:x[2])
        df['liquidity']=df['data_decoded'].map(lambda x:x[0])
        return {'hash':df['transactionHash'][0],'time':df['create_time'][0],'nft_id':nft_id,'token0_amount':df['token0'][0],'token1_amount':df['token1'][0],'liquidity':df['liquidity'][0]}
    else:
        raise Exception('fetched None')

def get_decrease_liquidity_by_nft_id(
        connection,
        nft_id):
    fb=0
    tb=connection.eth.block_number
    cAddress="0xc36442b4a4522e871399cd717abdd847ab11fe88"
    tp=["0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4",'0x'+hex(nft_id)[2:].rjust(64,'0')]
    # tp=["0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f"]

    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        df=pd.read_json(temp)
        #get the timestamp of each transaction
        df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        #{"indexed":false,"internalType":"uint128","name":"liquidity","type":"uint128"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"IncreaseLiquidity","type":"event"}
        df['data_decoded'] = df['data'].map(
            lambda x: decode(
                ['uint256', 'uint256', 'uint256'],
                bytes.fromhex(x[2:] if x.startswith('0x') else x)
            )
        )
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        df['token0']=df['data_decoded'].map(lambda x:x[1])
        df['token1']=df['data_decoded'].map(lambda x:x[2])
        df['liquidity']=df['data_decoded'].map(lambda x:x[0])
        return {'hash':df['transactionHash'][0],'time':df['create_time'][0],'nft_id':nft_id,'token0_amount':df['token0'][0],'token1_amount':df['token1'][0],'liquidity':df['liquidity'][0]}
    else:
        return {'hash':None,'time':None,'nft_id':nft_id,'token0_amount':0,'token1_amount':0,'liquidity':0}
        # raise Exception('fetched None')

def get_collected_by_nft_id(
        connection,
        nft_id):
    principal=get_decrease_liquidity_by_nft_id(connection,nft_id)
    fb=0
    tb=connection.eth.block_number
    cAddress="0xc36442b4a4522e871399cd717abdd847ab11fe88"
    tp=["0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01",'0x'+hex(nft_id)[2:].rjust(64,'0')]
    # tp=["0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f"]

    result=connection.eth.get_logs(
        {"address": Web3.to_checksum_address(cAddress), 
    "topics":tp,
    "fromBlock":Web3.to_hex(fb),
    "toBlock":Web3.to_hex(tb)
    })
    if result!=[]:
        temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
        df=pd.read_json(temp)
        #get the timestamp of each transaction
        df['timeStamp']=df['blockNumber'].map(lambda x:connection.eth.get_block(x)['timestamp'])
        #calculate time stamp to datetime
        df['create_time']=df['timeStamp'].map(lambda x:time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(x)))
        #decode the data
        #{"indexed":false,"internalType":"uint128","name":"liquidity","type":"uint128"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"IncreaseLiquidity","type":"event"}
        df['data_decoded']=df['data'].map(lambda x:decode(['uint256','uint256','uint256'],bytes.fromhex(x[2:])))
        # df['data_decoded']=df['data_decoded'].map(lambda x:eval(x))
        #split data_decoded to 3 columns
        
        df['token0_fee']=df['data_decoded'].map(lambda x:x[1])-principal['token0_amount']
        df['token1_fee']=df['data_decoded'].map(lambda x:x[2])-principal['token1_amount']
        
        return {'collected':True,'hash':df['transactionHash'][0],'time':df['create_time'][0],'nft_id':nft_id,
                'fee_amount0':df['token0_fee'][0],'fee_amount1':df['token1_fee'][0],
                'principal0':principal['token0_amount'],'principal1':principal['token1_amount']}
    else:
        return {'collected':False,'hash':False,'time':False,'nft_id':nft_id,'fee_amount0':0,'fee_amount1':0,'principal0':0,'principal1':0}

# function to get range1 range2 from pool_infor and amount0,amount1,liquidity from nft_add amount with the same transaction hash of each nft_id in NFTS
def get_all_pools_by_address(address,w3,fb,tb):
    NFTS=get_NFTS_by_address(address,w3)
    nft_dct=[]
    number=0
    for nft_id in NFTS:
        print(number,'getting nft_id:',nft_id,'...')
        number+=1
        nft_add_amount=(get_increase_liquidity_by_nft_id(w3,nft_id,fb,tb))
        pool_infor=(get_pool_infor_by_nft_id(nft_id,w3))
        #combine nft_add_amount and pool_infor into dct
        nft_dct1={**nft_add_amount,**pool_infor}
        #append nft_dct to nft_dct
        nft_dct.append(nft_dct1)
    #convert nft_dct to dataframe
    nft_df=pd.DataFrame(nft_dct)
    return nft_df

#help create a function to get uniswap v3 through web3 directly not through thegraph
def get_fee_growth_global(pool_address,w3):
    fee_growth_global0_abi={
        "inputs":[],"name":"feeGrowthGlobal0X128",
        "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
        "stateMutability":"view",
        "type":"function"}
    contract=w3.eth.contract(address=Web3.to_checksum_address(pool_address.lower()),abi=[fee_growth_global0_abi])
    fee_growth_global0=contract.functions.feeGrowthGlobal0X128().call()
    fee_growth_global1_abi={
        "inputs":[],"name":"feeGrowthGlobal1X128",
        "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
        "stateMutability":"view",
        "type":"function"}
    contract=w3.eth.contract(address=Web3.to_checksum_address(pool_address.lower()),abi=[fee_growth_global1_abi])
    fee_growth_global1=contract.functions.feeGrowthGlobal1X128().call()
    return {'fee_growth_global0':fee_growth_global0,'fee_growth_global1':fee_growth_global1}

def get_fee_growth_outside(pool_address,w3,tick):
    ticks_abi={"inputs":[{"internalType":"int24","name":"","type":"int24"}],"name":"ticks","outputs":[{"internalType":"uint128","name":"liquidityGross","type":"uint128"},{"internalType":"int128","name":"liquidityNet","type":"int128"},{"internalType":"uint256","name":"feeGrowthOutside0X128","type":"uint256"},{"internalType":"uint256","name":"feeGrowthOutside1X128","type":"uint256"},{"internalType":"int56","name":"tickCumulativeOutside","type":"int56"},{"internalType":"uint160","name":"secondsPerLiquidityOutsideX128","type":"uint160"},{"internalType":"uint32","name":"secondsOutside","type":"uint32"},{"internalType":"bool","name":"initialized","type":"bool"}],"stateMutability":"view","type":"function"}
    contract=w3.eth.contract(address=Web3.to_checksum_address(pool_address.lower()),abi=[ticks_abi])
    fee_growth_outside=contract.functions.ticks(tick).call()
    return {'fee_growth_outside0':fee_growth_outside[2],'fee_growth_outside1':fee_growth_outside[3]}

def get_fee_growth_inside(pool_address,w3,nft_id):
    position_abi={"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"positions",
                  "outputs":[{"internalType":"uint96","name":"nonce","type":"uint96"},
                             {"internalType":"address","name":"operator","type":"address"},
                             {"internalType":"address","name":"token0","type":"address"},
                             {"internalType":"address","name":"token1","type":"address"},
                             {"internalType":"uint24","name":"fee","type":"uint24"},
                             {"internalType":"int24","name":"tickLower","type":"int24"},
                             {"internalType":"int24","name":"tickUpper","type":"int24"},
                             {"internalType":"uint128","name":"liquidity","type":"uint128"},
                             {"internalType":"uint256","name":"feeGrowthInside0LastX128","type":"uint256"},
                             {"internalType":"uint256","name":"feeGrowthInside1LastX128","type":"uint256"},
                             {"internalType":"uint128","name":"tokensOwed0","type":"uint128"},
                             {"internalType":"uint128","name":"tokensOwed1","type":"uint128"}],
                             "stateMutability":"view","type":"function"}
    contract=w3.eth.contract(address=Web3.to_checksum_address(pool_address.lower()),abi=[position_abi])
    fee_growth_inside=contract.functions.positions(nft_id).call()
    decimals0=get_decimals_by_address(fee_growth_inside[2],w3)
    decimals1=get_decimals_by_address(fee_growth_inside[3],w3)
    symbol0=get_symbol_by_address(fee_growth_inside[2],w3)
    symbol1=get_symbol_by_address(fee_growth_inside[3],w3)
    #return decimals0,decimals1,liquidity,tick_lower,tick_upper,fee_growth_inside0,fee_growth_inside1
    return {'symbol0':symbol0,'symbol1':symbol1,'decimals0':decimals0,'decimals1':decimals1,'tick_lower':fee_growth_inside[5],'tick_upper':fee_growth_inside[6],
            'liquidity':fee_growth_inside[7],'fee_growth_inside0':fee_growth_inside[8],'fee_growth_inside1':fee_growth_inside[9]}

def get_calc_fees_params(pool_address,nft_id,w3):

    fee_growth_global=get_fee_growth_global(pool_address,w3)
    fee_growth_inside=get_fee_growth_inside('0xC36442b4a4522E871399CD717aBDD847Ab11FE88',w3,nft_id)
    liquidity=fee_growth_inside['liquidity']
    tick_lower=fee_growth_inside['tick_lower']
    tick_upper=fee_growth_inside['tick_upper']
    fee_growth_inside0=fee_growth_inside['fee_growth_inside0']
    fee_growth_inside1=fee_growth_inside['fee_growth_inside1']
    symbol0=fee_growth_inside['symbol0']
    symbol1=fee_growth_inside['symbol1']
    decimals0=fee_growth_inside['decimals0']
    decimals1=fee_growth_inside['decimals1']
    fee_growth_outside_tick_lower=get_fee_growth_outside(pool_address,w3,tick_lower)
    fee_growth_outside_tick_upper=get_fee_growth_outside(pool_address,w3,tick_upper)
    fee_growth_outside0_tick_lower=fee_growth_outside_tick_lower['fee_growth_outside0']
    fee_growth_outside1_tick_lower=fee_growth_outside_tick_lower['fee_growth_outside1']
    fee_growth_outside0_tick_upper=fee_growth_outside_tick_upper['fee_growth_outside0']
    fee_growth_outside1_tick_upper=fee_growth_outside_tick_upper['fee_growth_outside1']
    fee_growth_global0=fee_growth_global['fee_growth_global0']
    fee_growth_global1=fee_growth_global['fee_growth_global1']
    return {'symbol0':symbol0,'symbol1':symbol1,'liquidity':liquidity,'tick_lower':tick_lower,'tick_upper':tick_upper,'fee_growth_inside0':fee_growth_inside0,'fee_growth_inside1':fee_growth_inside1,'decimals0':decimals0,'decimals1':decimals1,'fee_growth_outside0_tick_lower':fee_growth_outside0_tick_lower,'fee_growth_outside1_tick_lower':fee_growth_outside1_tick_lower,'fee_growth_outside0_tick_upper':fee_growth_outside0_tick_upper,'fee_growth_outside1_tick_upper':fee_growth_outside1_tick_upper,'fee_growth_global0':fee_growth_global0,'fee_growth_global1':fee_growth_global1}

def get_sqrtprice(pool_address,w3):
    pool_abi={"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},
                                                   {"internalType":"int24","name":"tick","type":"int24"},
                                                   {"internalType":"uint16","name":"observationIndex","type":"uint16"},
                                                   {"internalType":"uint16","name":"observationCardinality","type":"uint16"},
                                                   {"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},
                                                   {"internalType":"uint8","name":"feeProtocol","type":"uint8"},
                                                   {"internalType":"bool","name":"unlocked","type":"bool"}],
              "stateMutability":"view","type":"function"}
    contract=w3.eth.contract(address=Web3.to_checksum_address(pool_address.lower()),abi=[pool_abi])
    sqrtprice=contract.functions.slot0().call()
    return sqrtprice[0]

def calc_fees(calc_fees_params,current_tick):
        # liquidity,
        # current_tick, min_tick, max_tick,
        # global_fee_growth0x128, global_fee_growth1x128,
        # min_tick_fee_growth_outside0x128, min_tick_fee_growth_outside1x128,
        # max_tick_fee_growth_outside0x128, max_tick_fee_growth_outside1x128,
        # fee_growth_inside_last0x128, fee_growth_inside_last1x128,
        # decimals0, decimals1,

        '''
        Calculate the accumulated fee income in a Uniswap V3 liquidity provision position,
        across the two tokens in the pool.
        Based on 'https://gist.github.com/Lucas-Kohorst/3b2727eaa60edebc27b21c7195261865/' but
        with bug fixes around under- and over-flow.
        if liquidity==0,return 0 
        '''
        liquidity = calc_fees_params['liquidity']
        min_tick = calc_fees_params['tick_lower']
        max_tick = calc_fees_params['tick_upper']
        global_fee_growth0x128 = calc_fees_params['fee_growth_global0']
        global_fee_growth1x128 = calc_fees_params['fee_growth_global1']
        min_tick_fee_growth_outside0x128 = calc_fees_params['fee_growth_outside0_tick_lower']
        min_tick_fee_growth_outside1x128 = calc_fees_params['fee_growth_outside1_tick_lower']
        max_tick_fee_growth_outside0x128 = calc_fees_params['fee_growth_outside0_tick_upper']
        max_tick_fee_growth_outside1x128 = calc_fees_params['fee_growth_outside1_tick_upper']
        fee_growth_inside_last0x128 = calc_fees_params['fee_growth_inside0']
        fee_growth_inside_last1x128 = calc_fees_params['fee_growth_inside1']
        decimals0 = calc_fees_params['decimals0']
        decimals1 = calc_fees_params['decimals1']

        # Check out the relevant formulas below which are from Uniswap Whitepaper Section 6.3 and 6.4
        # 𝑓𝑟 = 𝑓𝑔−𝑓𝑏(𝑖𝑙)−𝑓𝑎(𝑖𝑢)
        # 𝑓𝑢 = 𝑙·(𝑓𝑟(𝑡1)−𝑓𝑟(𝑡0))
        if liquidity!=0:
            # Global fee growth per liquidity '𝑓𝑔' for both token 0 and token 1
            global_fee_growth0 = UFlow(global_fee_growth0x128, num_bits=256)
            global_fee_growth1 = UFlow(global_fee_growth1x128, num_bits=256)

            # Fee growth outside '𝑓𝑜' of our lower tick for both token 0 and token 1
            min_tick_fee_growth_outside0 = UFlow(min_tick_fee_growth_outside0x128, num_bits=256)
            min_tick_fee_growth_outside1 = UFlow(min_tick_fee_growth_outside1x128, num_bits=256)

            # Fee growth outside '𝑓𝑜' of our upper tick for both token 0 and token 1
            max_tick_fee_growth_outside0 = UFlow(max_tick_fee_growth_outside0x128, num_bits=256)
            max_tick_fee_growth_outside1 = UFlow(max_tick_fee_growth_outside1x128, num_bits=256)

            # NOTE assume intermediate values need to over- or under-flow the same as e.g. feeGrowthGlobal
            # These are '𝑓𝑏(𝑖𝑙)' and '𝑓𝑎(𝑖𝑢)' from the formula for both token 0 and token 1
            min_tick_fee_growth_below0, min_tick_fee_growth_below1 = UFlow(0, num_bits=256), UFlow(0, num_bits=256)
            max_tick_fee_growth_above0, max_tick_fee_growth_above1 = UFlow(0, num_bits=256), UFlow(0, num_bits=256)

            # These are the calculations for '𝑓𝑎(𝑖)' from the formula for both token 0 and token 1
            if current_tick >= max_tick:
                max_tick_fee_growth_above0 = global_fee_growth0 - max_tick_fee_growth_outside0
                max_tick_fee_growth_above1 = global_fee_growth1 - max_tick_fee_growth_outside1
            else:
                max_tick_fee_growth_above0 = max_tick_fee_growth_outside0
                max_tick_fee_growth_above1 = max_tick_fee_growth_outside1

            # These are the calculations for '𝑓b(𝑖)' from the formula for both token 0 and token 1
            if current_tick >= min_tick:
                min_tick_fee_growth_below0 = min_tick_fee_growth_outside0
                min_tick_fee_growth_below1 = min_tick_fee_growth_outside1
            else:
                min_tick_fee_growth_below0 = global_fee_growth0 - min_tick_fee_growth_outside0
                min_tick_fee_growth_below1 = global_fee_growth1 - min_tick_fee_growth_outside1

            # Calculations for '𝑓𝑟(𝑡1)' part of the '𝑓𝑢 = 𝑙·(𝑓𝑟(𝑡1)−𝑓𝑟(𝑡0))' formula for both token 0 and token 1
            fr_t1_0 = global_fee_growth0 - min_tick_fee_growth_below0 - max_tick_fee_growth_above0
            fr_t1_1 = global_fee_growth1 - min_tick_fee_growth_below1 - max_tick_fee_growth_above1

            # '𝑓𝑟(𝑡0)' part of the '𝑓𝑢 =𝑙·(𝑓𝑟(𝑡1)−𝑓𝑟(𝑡0))' formula for both token 0 and token 1
            fee_growth_inside_last0 = UFlow(fee_growth_inside_last0x128, num_bits=256)
            fee_growth_inside_last1 = UFlow(fee_growth_inside_last1x128, num_bits=256)

            # Calculations for the '𝑓𝑢 = 𝑙·(𝑓𝑟(𝑡1)−𝑓𝑟(𝑡0))' uncollected fees formula for both token 0 and token 1
            fees0 = int(liquidity) * ((fr_t1_0 - fee_growth_inside_last0).num / (2 ** 128))
            fees1 = int(liquidity) * ((fr_t1_1 - fee_growth_inside_last1).num / (2 ** 128))

            # Decimal adjustment to get final results
            adj_fees0 = fees0 / (10 ** int(decimals0))
            adj_fees1 = fees1 / (10 ** int(decimals1))
        else:
            adj_fees0=0
            adj_fees1=0
        return dict(
            token0=adj_fees0, token1=adj_fees1,
        )

def calc_fees_and_withdrawable(calc_fees_params,w3,pool_address):
        # liquidity,
        # current_tick, min_tick, max_tick,
        # global_fee_growth0x128, global_fee_growth1x128,
        # min_tick_fee_growth_outside0x128, min_tick_fee_growth_outside1x128,
        # max_tick_fee_growth_outside0x128, max_tick_fee_growth_outside1x128,
        # fee_growth_inside_last0x128, fee_growth_inside_last1x128,
        # decimals0, decimals1,

        '''
        Calculate the accumulated fee income in a Uniswap V3 liquidity provision position,
        across the two tokens in the pool.
        Based on 'https://gist.github.com/Lucas-Kohorst/3b2727eaa60edebc27b21c7195261865/' but
        with bug fixes around under- and over-flow.
        if liquidity==0,return 0 
        '''
        liquidity = calc_fees_params['liquidity']
        min_tick = calc_fees_params['tick_lower']
        max_tick = calc_fees_params['tick_upper']
        decimals0 = calc_fees_params['decimals0']
        decimals1 = calc_fees_params['decimals1']

        # Check out the relevant formulas below which are from Uniswap Whitepaper Section 6.3 and 6.4
        # 𝑓𝑟 = 𝑓𝑔−𝑓𝑏(𝑖𝑙)−𝑓𝑎(𝑖𝑢)
        # 𝑓𝑢 = 𝑙·(𝑓𝑟(𝑡1)−𝑓𝑟(𝑡0))
        if liquidity!=0:
            current_price=get_current_price_by_pool_address(w3,pool_address,1)['price0']
            current_tick=price_to_tick(current_price,decimals0,decimals1)
            fee=calc_fees(calc_fees_params,current_tick)
            sqrt_price_x96=get_sqrtprice(pool_address,w3)
            withdraw=calc_withdrawable_tokens(liquidity, current_tick, min_tick, max_tick, sqrt_price_x96, decimals0, decimals1)
            adj_fees0=fee['token0']
            adj_fees1=fee['token1']
            adj_amt0=withdraw['token0']
            adj_amt1=withdraw['token1']
        else:
            adj_fees0=0
            adj_fees1=0
            adj_amt0=0
            adj_amt1=0
            current_price=None
        return dict(
            fee0=adj_fees0, fee1=adj_fees1,amt0=adj_amt0,amt1=adj_amt1,
            current_price=current_price
        )

def calc_tick_price(tick):
    '''
    Price a certain, signed-integer tick index represents.
    '''
    return 1.0001 ** int(tick)

def calc_withdrawable_tokens(liquidity, current_tick, min_tick, max_tick, sqrt_price_x96, decimals0, decimals1):
        '''
        Calculate the amount of each token that could be withdrawn from
        a Uniswap V3 liquidity position. Based on a Discord conversation
        with @Crypto_Rachel on #dev-chat on Uniswap.
        if liquidity=0,all are 0
        '''
        if liquidity!=0:
            sqrt_price = int(sqrt_price_x96) / (2 ** 96) 
            sqrt_min_price = calc_tick_price(min_tick) ** 0.5
            sqrt_max_price = calc_tick_price(max_tick) ** 0.5

            amt0, amt1 = 0, 0
            if current_tick <= min_tick:
                amt0 = np.floor(int(liquidity) * ((sqrt_max_price - sqrt_min_price) / (sqrt_min_price * sqrt_max_price)))
            elif current_tick >= max_tick:
                amt1 = np.floor(int(liquidity) * (sqrt_max_price - sqrt_min_price))
            else:  # (current_tick > min_tick) and (current_tick < max_tick):
                amt0 = np.floor(int(liquidity) * ((sqrt_max_price - sqrt_price) / (sqrt_price * sqrt_max_price)))
                amt1 = np.floor(int(liquidity) * (sqrt_price - sqrt_min_price))

            adj_amt0 = amt0 / (10 ** int(decimals0))
            adj_amt1 = amt1 / (10 ** int(decimals1))
        else:
            adj_amt0=0
            adj_amt1=0
        return dict(
            token0=adj_amt0, token1=adj_amt1,
        )   


def get_output_by_nft_id(nft_id,w3,factory_contract,nft_position_manager):
    #record running time of each line
    # start_time=time.time()
    pool_infor=get_pool_infor_by_nft_id(nft_id,nft_position_manager)
    # end_time=time.time()
    # print("get_pool_infor_by_nft_id running time: ",end_time-start_time)
    pool_address=factory_contract.functions.getPool(pool_infor['token0'],pool_infor["token1"],pool_infor['fee']).call()
    # start_time=time.time()
    fees_params=get_calc_fees_params(pool_address,nft_id,w3)
    # end_time=time.time()
    # print("get_calc_fees_params running time: ",end_time-start_time)
    # current_tick=price_to_tick(current_price,fees_params['decimals0'],fees_params['decimals1'])
    # 
    fee_and_withdraw=calc_fees_and_withdrawable(fees_params,w3,pool_address)
    initial_add=get_increase_liquidity_by_nft_id(w3,nft_id)
    collected=get_collected_by_nft_id(w3,nft_id)
    initial_timestamp=time.mktime(datetime.strptime(initial_add['time'],'%Y-%m-%d %H:%M:%S').timetuple())
    if collected['collected']==False: 
        duration=(time.time()-initial_timestamp)/(60*60)
        collected_time=False
        
    else:
        collect_timestamp=time.mktime(datetime.strptime(collected['time'],'%Y-%m-%d %H:%M:%S').timetuple())
        duration=(collect_timestamp-initial_timestamp)/(60*60)
        collected_time=collected['time']
    
    return dict(
        nft_id=nft_id,
        symbol0=fees_params['symbol0'],symbol1=fees_params['symbol1'],
        
        tick_lower=tick_to_price(fees_params['tick_lower'],fees_params["decimals0"],fees_params["decimals1"]),
        tick_upper=tick_to_price(fees_params['tick_upper'],fees_params["decimals0"],fees_params["decimals1"]),
        current_fee0=fee_and_withdraw['fee0'],
        current_fee1=fee_and_withdraw['fee1'],
        withdrawable_tokens0=fee_and_withdraw['amt0'],
        withdrawable_tokens1=fee_and_withdraw['amt1'],
        liquidity=fees_params['liquidity'],
        create_time=initial_add['time'],
        create_token0=initial_add['token0_amount']/10**fees_params['decimals0'],
        create_token1=initial_add['token1_amount']/10**fees_params['decimals1'],
        create_hash=initial_add['hash'],
        collected=collected['collected'],
        collected_time=collected_time,
        collected_fee_token0=collected['fee_amount0']/10**fees_params['decimals0'],
        collected_fee_token1=collected['fee_amount1']/10**fees_params['decimals1'],
        collected_hash=collected['hash'],
        collected_principal_token0=collected['principal0']/10**fees_params['decimals0'],
        collected_principal_token1=collected['principal1']/10**fees_params['decimals1'],
        duration=duration,
        current_price=fee_and_withdraw['current_price']
        )


def get_current_price_by_pool_address(
        connection,pool_address,n
    ):
    # fb=74711249,tb=74811249
    try:
        fb=connection.eth.block_number-n*500
        tb=connection.eth.block_number
        cAddress=pool_address
        tp=["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"]

        result=connection.eth.get_logs(
            {"address": Web3.to_checksum_address(cAddress), 
        "topics":tp,
        "fromBlock":Web3.to_hex(fb),
        "toBlock":Web3.to_hex(tb)
        })
        if result!=[]:
            temp=Web3.to_json(result)#result is a list of attributeDict type,convert attributeDict to json
            
            df=pd.read_json(temp).tail(1)
            timestamp_end=connection.eth.get_block(int(df['blockNumber'].tail(1)))['timestamp']
            date=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp_end))

            df['data_decoded']=df['data'].map(lambda x:decode(['int256','int256','int256'],bytes.fromhex(x[2:])))
            df['amount0']=abs(df['data_decoded'].map(lambda x:x[0]))
            df['amount1']=abs(df['data_decoded'].map(lambda x:x[1]))
            if pool_address.lower()=='0xc6f780497a95e246eb9449f5e4770916dcd6396a':
                decimals1=18
            else:
                decimals1=6 #USDC
            decimals0=18 #ETH
            price0 = df['amount1']/10**decimals1/(df['amount0']/10**decimals0)
            # Calculate the price of token0 in terms of token1
            price1 = 1 / price0
            # return the value of price0

            return dict(date=date,price0=price0.values[0])
        
        else:
            raise Exception('no data')
    except:
        print('retry...')
        return get_current_price_by_pool_address(
        connection,pool_address,n+1)


def get_all_nft_data(w3,nft_position_manager,factory_contract,current_price):
    with open('nfts_list.json') as f:
        nft_ids = json.load(f)
    nft_data=[]
    for nft in nft_ids:
        nft_id=nft['nft_id']
        
        output=get_output_by_nft_id(nft_id,current_price,w3,factory_contract,nft_position_manager)
        nft_data.append(output)
        with open (r'nft_data.json','w') as f:
            json.dump(nft_data,f)
        print(nft['index'],'...get data finished')
    return nft_data

def get_nft_data_since_last_index(w3,nft_position_manager,factory_contract,current_price,last_index):
    with open('nfts_list.json') as f:
        nft_list = json.load(f)
    #the length of nft_ids
    nft_list_len=len(nft_list)
    nft_list_df=pd.DataFrame(nft_list)
    if last_index==0:
        nft_data=[]
    else:
        with open('nft_data.json') as f:
            nft_data = json.load(f)
    index=last_index
    while index<=nft_list_len:
        nft_id=nft_list_df[nft_list_df['index']==index]['nft_id'].values[0]
        output=get_output_by_nft_id(int(nft_id),w3,factory_contract,nft_position_manager)
        #contact output and nft['index'] to get the new output
        output=dict(output,**{'index':index})
        nft_data.append(output)
        with open (r'nft_data.json','w') as f:
            json.dump(nft_data,f)       
        print(index,'...nft data finished')
        index=index+1
    return nft_data

def send_data_to_server(nft_list):
    url='http://42.192.17.155/nft_list'
    
    json_data = bytes(json.dumps(nft_list, ensure_ascii=False).encode('utf-8'))
    # Send the JSON data to the server
    response = requests.post(url, data=json_data)
    # Check if the POST request was successful
    if response.status_code == 200:
        print("Data successfully sent to server.")
    else:
        print("Failed to send data to server.")

def update_nft_list(wallet_address,w3,nft_position_manager):
    #update nft list to the current time and save to json file
    #load json file
#     with open('nfts_list.json') as f:
#         nfts_list = json.load(f)
    url='http://42.192.17.155/nft_list'
    response = requests.get(url)
    assert response.status_code==200
    nfts_list=response.json()
    #convert nft_list to dataframe
    df=pd.DataFrame(nfts_list)
    #select the lastest index from dataframe
    last_index=df['index'].max()
    #convert last_index to int256
    last_index=int(last_index)
    #select open nfts from dataframe
    df_open=df[df['closed']=='open']
    #get the nft_ids of open nfts and its liquidity ,if the liquidity is 0,set the colosed to 'closed'
    for index,row in df_open.iterrows():
        nft_id=row['nft_id']
        liquidity=get_pool_infor_by_nft_id(nft_id,nft_position_manager)['liquidity']
        if liquidity==0:
            df.loc[index,'closed']='closed'
    #convert df to list
    nfts_list=df.to_dict('records')
    #get the new nfts
    new_nfts=get_new_NFTS_by_address(wallet_address,w3,nft_position_manager,last_index)
    #append new_nfts to nft_list
    nfts_list.extend(new_nfts)
    #save nft_list to json file
    # update_time=time.strftime("%Y_%m_%d_%H_%M_%S",time.time())
    send_data_to_server(nfts_list)
    #dont delete below
    # with open('nfts_list.json', 'w') as f:
    #     json.dump(nfts_list, f)

def update_nft_data(w3,factory_contract,current_price):
    with open('nfts_list.json') as f:
        nft_list = json.load(f)
    nft_balance=len(nft_list)
    print('nft balance from nft_list is',nft_balance)

    with open('nft_data.json') as f:
        nft_data = json.load(f)
    df3=pd.DataFrame(nft_data)
    last_index=df3['index'].max()
    print('last saved data index is',last_index)
    last_index=int(last_index)+1
    try:
        nft_data=get_nft_data_since_last_index(w3,factory_contract,current_price,last_index)
    except:
        print('error,retry get nft_data...')
        with open('nft_data.json') as f:
            nft_data = json.load(f)
        df3=pd.DataFrame(nft_data)
        last_index=df3['index'].max()
        last_index=int(last_index)+1
        print('retry from',last_index)
        if last_index<nft_balance:
            nft_data=update_nft_data(w3,factory_contract,current_price,last_index)
    return nft_data

# the intial parameters

# factory_address='0x1F98431c8aD98523631AE4a59f267346ea31F984'
# contract_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
# provider_arb='https://arb1.arbitrum.io/rpc'
# provider_arb_2='https://arbitrum-mainnet.infura.io/v3/02040948aa024dc49e8730607e0caece'

# w3=Web3(HTTPProvider(provider_arb_2, {'timeout': 20}))

# with open(r"arbitrum nft position manager v3 ABI.json") as json_file:
#         contract_abi = json.load(json_file)
# nft_position_manager=w3.eth.contract(
#     address=Web3.to_checksum_address(contract_address.lower()),abi=contract_abi)

# with open(r"factory abi.json") as json_file:
#         factory_abi = json.load(json_file)
# factory_contract=w3.eth.contract(address=Web3.to_checksum_address(factory_address.lower()),abi=factory_abi)
# wallet_address='0x9742499f4f1464c5b3dbf4d04adcbc977fbf7baa'


# try:
#     update_nft_list(wallet_address,w3,nft_position_manager)
# except:
#     print('error,retry...')
#     update_nft_list(wallet_address,w3,nft_position_manager)
# print('update nft_list finished,wallet address ',wallet_address)

# current_price=get_current_price_by_pool_address(w3,'0xc6f780497a95e246eb9449f5e4770916dcd6396a',1)['price0']
# nft=get_nft_data_since_last_index(w3,nft_position_manager,factory_contract,current_price,291)
# # 240 missed
# c=1
# #update nft_list of a address
# try:
#     update_nft_list(wallet_address,w3,nft_position_manager)
# except:
#     print('error,retry...')
#     update_nft_list(wallet_address,w3,nft_position_manager)
# print('update nft_list finished,wallet address ',wallet_address)

# # update nft_data by nft_id which is already done by a address,first time, update since 0,use
# #nft_data=get_nft_data_since_last_index(w3,factory_contract,current_price,0)
# # nft_data=update_nft_data(w3,factory_contract,current_price)

# #open nft list and nft data json file
# with open('nfts_list.json') as f:
#      nfts_list=json.load(f)

# nft_list=pd.DataFrame(nfts_list)

# with open('nft_data.json') as f:
#      nft_data=json.load(f)
# df2=pd.DataFrame(nft_data)

# #select the nfts which is open from the nft_list 
# df=nft_list[nft_list['closed']=='open'][1:]#delete a unnormal one
# #get output of each nft in df by nft_id
# nft_data=[]
# for nft_id in df['nft_id']:
#     d=get_output_by_nft_id(nft_id,w3,factory_contract,nft_position_manager)
#     nft_data.append(d)
# #convert nft_data to dataframe
# nft_data=pd.DataFrame(nft_data)
# #save nft_data to csv file
# nft_data.to_csv('nft_data_open.csv')
# print('get open nft_data finished,wallet address ',wallet_address)



# connection = Web3(HTTPProvider(provider_arb, {'timeout': 60}))
# address='0x9742499F4F1464C5B3dBf4d04ADcbc977fbf7baa'
# fb=0
# #get the latest block number
# tb=connection.eth.block_number




# # Define the Transfer event signature
# TRANSFER_EVENT_SIGNATURE = 'Transfer(address,address,uint256)'

# # Define the IncreaseLiquidity event signature
# INCREASE_LIQUIDITY_EVENT_SIGNATURE = 'IncreaseLiquidity(uint256,uint128,uint256,uint256)'

# # Get the block number when the position was created
# # creation_block_number = nft_position_manager.functions.tokenMintedAt(NFT_ID).call()

# transfer_filter_params = {
#     'address': contract_address,
#     'fromBlock': '0x0',
#     'toBlock': 'latest',
#     'topics': ['0x0000000000000000000000000000000000000000',
#         Web3.keccak(text="Transfer(address,address,uint256)").hex(),
#         # None,
#         '0x0000000000000000000000000000000000000000',
#         # '0x0000000000000000000000000000000000000000000000000000000000000000',
#         # '0x00000000000000000000000000000000000000',
#         # '  1234567890123456789012345678901234567890
#         Web3.to_checksum_address(address),
#         '0x'+hex(NFT_ID)[2:].rjust(64,'0')
#     ]
# }
# # transfer_filter_params['topics'] = [topic if topic is not None else None for topic in transfer_filter_params['topics']]
# transfer_events = w3.eth.get_logs(transfer_filter_params)
# # Use the eth_getLogs JSON-RPC method directly
# transfer_events = w3.provider.make_request("eth_getLogs", [transfer_filter_params])

# if not transfer_events['result']:
#     print("No transfer event found for the specified NFT ID")
# else:
#     transfer_event = transfer_events['result'][0]
#     creation_block_number = int(transfer_event['blockNumber'], 16)
#     creation_tx_hash = transfer_event['transactionHash']

# transfer_events = w3.eth.get_logs(transfer_filter_params)

# if not transfer_events:
#     print("No transfer event found for the specified NFT ID")
# else:
#     transfer_event = transfer_events[0]
#     creation_block_number = transfer_event['blockNumber']
#     creation_tx_hash = transfer_event['transactionHash']



    # Get the transaction receipt
    # tx_receipt = w3.eth.getTransactionReceipt(creation_tx_hash)

    # # Filter the IncreaseLiquidity events from the transaction receipt
    # increase_liquidity_events = nft_position_manager.events.IncreaseLiquidity.getLogs(tx_receipt)

    # if not increase_liquidity_events:
    #     print("No IncreaseLiquidity event found for the specified NFT ID")
    # else:
    #     # Get the specific IncreaseLiquidity event that corresponds to the position creation
    #     increase_liquidity_event = increase_liquidity_events[0]

    #     # Extract the amount of token0 added
    #     token0_amount_added = increase_liquidity_event['args']['amount0']

    #     print(f"Token0 amount added for NFT ID {NFT_ID}: {token0_amount_added}")

# # Some token addresses we'll be using later in this guide
# eth="0x0000000000000000000000000000000000000000"
# weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
# bat = "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
# dai = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
# usdc="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
# weth_arb="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
# usdc_arb="0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"
# weth_arb_test="0xB47e6A5f8b33b3F17603C83a0535A9dcD7E32681"

# provider ='https://rinkeby.infura.io/v3/02040948aa024dc49e8730607e0caece'
# provider_arb_test='https://arbitrum-rinkeby.infura.io/v3/02040948aa024dc49e8730607e0caece'
# provider_arb='https://arbitrum-mainnet.infura.io/v3/02040948aa024dc49e8730607e0caece'
# # provider_arb='https://arb1.arbitrum.io/rpc'
# provider_arb_2='https://arb-mainnet.g.alchemy.com/v2/jA4AWJHwRhOI-GPGBbMnmdCDAR4ks7u7'

# address = "0xD8Db274c42D115381d1Af91070A357CA90608363"   
       # or None if you're not going to make transactions


#b=uniswap.get_price_output(usdc_arb,weth_arb,1*10**18,500)

#b=uniswap.get_price_input(usdc_arb,weth_arb,1*10**18,500)

#print([b[0]/10**6,b[1]**2/2**192*10**12])



# c=1
# uniswap = Uniswap(address,key,version=3, provider=provider_arb)
# # balance_my=uniswap.get_eth_balance()/10**18
# # print("the ETH blance of Mybot: {:.2f}".format(balance_my))
# # add liquidity
# token0=weth_arb
# token1=usdc_arb
# fee=500
# tickLower=uniswap.price_to_tick(3300)
# tickUpper=uniswap.price_to_tick(3900)
# amount0Desired=9999999
# amount1Desired=0
# amount0Min=amount0Desired
# amount1Min=0
# recipient=address
# deadline=int(time.time()) + 200

# mint_paragms=[token0,token1,fee,tickLower,tickUpper,amount0Desired,amount1Desired,amount0Min,amount1Min,recipient,deadline]
# print(mint_paragms)
# sys.exit()

# uniswap.add_liquidity_v3(token0,token1,fee,tickLower,tickUpper,amount0Desired,amount1Desired,amount0Min,amount1Min,recipient,deadline)





# uniswap.mint_nft(token0,token1,fee,tickLower,tickUpper,amount0Desired,amount1Desired,amount0Min,amount1Min,recipient,deadline)



# t={'from': '0xD8Db274c42D115381d1Af91070A357CA90608363', 'value': '0x110d9316ec000', 'nonce': '0x2', 'to': '0xC36442b4a4522E871399CD717aBDD847Ab11FE88', 'data': '0x8831645600000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000ff970a61a04b1ca14834a43f5de4533ebddb5cc800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0519fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0765000000000000000000000000000000000000000000000000000110d9316ec000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000d8db274c42d115381d1af91070a357ca9060836300000000000000000000000000000000000000000000000000000000626106e2'}

# tt={'from': '0xD8Db274c42D115381d1Af91070A357CA90608363', 'value': '0x110d9316ec000', 'nonce': '0x2', 'to': '0xC36442b4a4522E871399CD717aBDD847Ab11FE88', 'data': '0x8831645600000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000ff970a61a04b1ca14834a43f5de4533ebddb5cc800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0274fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd02d80000000000000000000000000000000000000000000000001bc16d674ec7ffb300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001bc16d674ec7ffb300000000000000000000000000000000000000000000000000000000000000000000000000000000000000004c20be52295db0e1fd86d158d4ae7f31b69ee50e000000000000000000000000000000000000000000000000000000006256d858'}

# #0x8831645600000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000ff970a61a04b1ca14834a43f5de4533ebddb5cc800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0519fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0765000000000000000000000000000000000000000000000000000110d9316ec0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000110d9316ec0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000d8db274c42d115381d1af91070a357ca906083630000000000000000000000000000000000000000000000000000000062610e21

# #0x8831645600000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000ff970a61a04b1ca14834a43f5de4533ebddb5cc800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0274fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd02d80000000000000000000000000000000000000000000000001bc16d674ec7ffb300000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001bc16d674ec7ffb300000000000000000000000000000000000000000000000000000000000000000000000000000000000000004c20be52295db0e1fd86d158d4ae7f31b69ee50e000000000000000000000000000000000000000000000000000000006256d858
# #0x88316456000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb4800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0519fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0b9f000000000000000000000000000000000000000000000000000009184e72a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009184e72a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000d8db274c42d115381d1af91070a357ca9060836300000000000000000000000000000000000000000000000000000000626231ff
# #0x88316456000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb4800000000000000000000000000000000000000000000000000000000000001f4fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0519fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd0b9f000000000000000000000000000000000000000000000000000009184e72a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009184e72a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000d8db274c42d115381d1af91070a357ca9060836300000000000000000000000000000000000000000000000000000000626234c7
# ttt={'from': '0xD8Db274c42D115381d1Af91070A357CA90608363', 'value': '0x246139ca8000', 'nonce': '0x2', 'to': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45', 'data': '0x04e45aaf00000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000ff970a61a04b1ca14834a43f5de4533ebddb5cc800000000000000000000000000000000000000000000000000000000000001f4000000000000000000000000d8db274c42d115381d1af91070a357ca906083630000000000000000000000000000000000000000000000000000246139ca8000000000000000000000000000000000000000000000000000000000000001db930000000000000000000000000000000000000000000000000000000000000000'}
# b=web3.eth.estimate_gas(t)

# print(f"test result is {b}")
# sys.exit()


# uniswap.make_trade(weth_arb, usdc_arb, 4*10**10,fee=500)    # sell 1 DAI for USDC using the 0.05% fee pool (v3 only)
# sys.exit()






# uniswap.mint_nft(token0,token1,fee,tickLower,tickUpper,amount0Desired,amount1Desired,amount0Min,amount1Min,recipient,deadline)

# sys.exit()














#a=uniswap.get_price_input(eth, dai, 2*10**18)/10**18


#uniswap.make_trade(eth, bat, 1*10**18)  # sell 1 ETH for BAT



