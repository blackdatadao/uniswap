# import time,requests,json
# import pandas as pd
# import streamlit as st
# from gql import gql, Client
# from gql.transport.requests import RequestsHTTPTransport
# import math
# import sys
# import plotly.express as px
# import plotly.graph_objects as go
# import pandas as pd
# from datetime import datetime, timedelta

# client = Client(
#     transport=RequestsHTTPTransport(
#         # url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
#         url='https://api.thegraph.com/subgraphs/name/messari/uniswap-v3-arbitrum',
#         verify=True,
#         retries=5,
#     ))

# def tick_to_price(tick):
#     return TICK_BASE ** tick

# TICK_BASE = 1.0001

# def fee_tier_to_tick_spacing(fee_tier):
#     return {
#         100: 1,
#         500: 10,
#         3000: 60,
#         10000: 200
#     }.get(fee_tier, 60)



# POOL_ID = "0xc6f780497a95e246eb9449f5e4770916dcd6396a" #arb mainnet 0.05% ARB/ETH pool
# pool_query = """query get_pools($pool_id: ID!) {
#     liquidityPools(where: {id: $pool_id}) {
#         name
#         tick
#         totalLiquidity
#         fees {
#         feePercentage
#         }
#         symbol
#         inputTokens {
#         symbol
#         decimals
#         }
#     }
#     }"""

# # ethereum mainnet use tickIdx,arb mainnet use index
# tick_query = """query get_ticks($num_skip: Int, $pool_id: ID!) {
# ticks(skip: $num_skip, where: {pool: $pool_id}) {
#     index
#     liquidityNet
# }
# }"""


# try:
#     variables = {"pool_id": POOL_ID}
#     response = client.execute(gql(pool_query), variable_values=variables)

#     if len(response['liquidityPools']) == 0:
#         print("pool not found")
#         exit(-1)

#     pool = response['liquidityPools'][0]
#     current_tick = int(pool["tick"])
#     tick_spacing = fee_tier_to_tick_spacing(int(10000*pool["fees"][0]["feePercentage"]))

#     token0 = pool["inputTokens"][0]["symbol"]
#     token1 = pool["inputTokens"][1]["symbol"]
#     decimals0 = int(pool["inputTokens"][0]["decimals"])
#     decimals1 = int(pool["inputTokens"][1]["decimals"])
# except Exception as ex:
#     print("got exception while querying pool data:", ex)
#     exit(-1)

# # get tick info
# tick_mapping = {}
# num_skip = 0
# try:
#     while True:
#         print("Querying ticks, num_skip={}".format(num_skip))
#         variables = {"num_skip": num_skip, "pool_id": POOL_ID}
#         response = client.execute(gql(tick_query), variable_values=variables)

#         if len(response["ticks"]) == 0:
#             break
#         num_skip += len(response["ticks"])
#         for item in response["ticks"]:
#             tick_mapping[int(item["index"])] = int(item["liquidityNet"])
# except Exception as ex:
#     print("got exception while querying tick data:", ex)
#     exit(-1)

    
# # Start from zero; if we were iterating from the current tick, would start from the pool's total liquidity
# liquidity = 0

# # Find the boundaries of the price range
# min_tick = min(tick_mapping.keys())
# max_tick = max(tick_mapping.keys())

# # Compute the tick range. This code would work as well in Python: `current_tick // tick_spacing * tick_spacing`
# # However, using floor() is more portable.
# current_range_bottom_tick = math.floor(current_tick / tick_spacing) * tick_spacing

# current_price = tick_to_price(current_tick)
# adjusted_current_price = current_price / (10 ** (decimals1 - decimals0))

# # Sum up all tokens in the pool
# total_amount0 = 0
# total_amount1 = 0


# # Guess the preferred way to display the price;
# # try to print most assets in terms of USD;
# # if that fails, try to use the price value that's above 1.0 when adjusted for decimals.
# stablecoins = ["USDC", "DAI", "USDT", "TUSD", "LUSD", "BUSD", "GUSD", "UST"]
# if token0 in stablecoins and token1 not in stablecoins:
#     invert_price = True
# elif adjusted_current_price < 1.0:
#     invert_price = True
# else:
#     invert_price = False

# # Iterate over the tick map starting from the bottom
# #create a dataframe to store the the tick, price,adjusted_amount0,adjusted_amount1
# amount_mapping = {}
# i=0
# tick = min_tick
# while tick <= max_tick:
#     liquidity_delta = tick_mapping.get(tick, 0)
#     liquidity += liquidity_delta

#     price = tick_to_price(tick)
#     adjusted_price = price / (10 ** (decimals1 - decimals0))
#     if invert_price:
#         adjusted_price = 1 / adjusted_price
#         tokens = "{} for {}".format(token0, token1)
#     else:
#         tokens = "{} for {}".format(token1, token0)

#     should_print_tick = liquidity != 0
#     # if should_print_tick:
#     #     print("ticks=[{}, {}], bottom tick price={:.6f} {}".format(tick, tick + tick_spacing, adjusted_price, tokens))

#     # Compute square roots of prices corresponding to the bottom and top ticks
#     bottom_tick = tick
#     top_tick = bottom_tick + tick_spacing
#     sa = tick_to_price(bottom_tick // 2)
#     sb = tick_to_price(top_tick // 2)

#     if tick < current_range_bottom_tick:
#         # Compute the amounts of tokens potentially in the range
#         amount1 = liquidity * (sb - sa)
#         amount0 = amount1 / (sb * sa)

#         # Only token1 locked
#         total_amount1 += amount1

#         if should_print_tick:
#             adjusted_amount0 = amount0 / (10 ** decimals0)
#             adjusted_amount1 = amount1 / (10 ** decimals1)
#             # print("        {:.10f} {} locked, potentially worth {:.2f} {}".format(adjusted_amount1, token1, adjusted_amount0, token0))
        
#             amount_mapping[tick] = [adjusted_price,0,adjusted_amount1]

#     elif tick == current_range_bottom_tick:
#         # Always print the current tick. It normally has both assets locked
#         # print("        Current tick, both assets present!")
#         print("        Current price={:.6f} {}".format(1 / adjusted_current_price if invert_price else adjusted_current_price, tokens))
#         current_price=1 / adjusted_current_price if invert_price else adjusted_current_price
#         # Print the real amounts of the two assets needed to be swapped to move out of the current tick range
#         current_sqrt_price = tick_to_price(current_tick / 2)
#         amount0actual = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
#         amount1actual = liquidity * (current_sqrt_price - sa)
#         adjusted_amount0actual = amount0actual / (10 ** decimals0)
#         adjusted_amount1actual = amount1actual / (10 ** decimals1)

#         total_amount0 += amount0actual
#         total_amount1 += amount1actual

#         # print("        {:.2f} {} and {:.2f} {} remaining in the current tick range".format(
#         #     adjusted_amount0actual, token0, adjusted_amount1actual, token1))
        
#         amount_mapping[tick] = [adjusted_price,adjusted_amount0,adjusted_amount1]

#     else:
#         # Compute the amounts of tokens potentially in the range
#         amount1 = liquidity * (sb - sa)
#         amount0 = amount1 / (sb * sa)

#         # Only token0 locked
#         total_amount0 += amount0

#         if should_print_tick:
#             adjusted_amount0 = amount0 / (10 ** decimals0)
#             adjusted_amount1 = amount1 / (10 ** decimals1)
#             # print("        {:.10f} {} locked, potentially worth {:.2f} {}".format(adjusted_amount0, token0, adjusted_amount1, token1))
        
#             amount_mapping[tick] = [adjusted_price,adjusted_amount0,0]
    
#     tick += tick_spacing
# #convert tick_mapping to dataframe

# df = pd.DataFrame(list(tick_mapping.items()),columns = ['tick','liquidityNet'])

# #print the length of the amount_mapping
# # print(len(tick_mapping))
# # print(len(amount_mapping))
# # print((max_tick-min_tick)/tick_spacing+1)

# #convert amount_mapping to dataframe with columns tick,price,amount0,amount1
# df2 = pd.DataFrame(list(amount_mapping.items()),columns = ['tick','price'])
# df2['amount0'] = df2['tick'].map(lambda x: amount_mapping[x][1])
# df2['amount1'] = df2['tick'].map(lambda x: amount_mapping[x][2])
# df2["price"]=df2["price"].map(lambda x: x[0])

# #extract the data from current_range_bottom_tick - 60 to current_range_bottom_tick + 60
# left = df2[(df2['tick'] >= current_range_bottom_tick - 0) & (df2['tick'] <= current_range_bottom_tick+1500)]
# right = df2[(df2['tick'] >= current_range_bottom_tick -1500) & (df2['tick'] <= current_range_bottom_tick-1)]
# #plot 柱状图 and show the amount0 of df2,price is the x axis amount0 is the y axis
# #show the y axis value when hover
# # use plotly.graph_objects go

# fig_left = go.Figure(go.Bar(
#     x=left['price'],
#     y=left['amount0'],
#     text=left['amount0'],  # Set bar text
#     textposition='outside'  # Position text outside of bars
# ))
# # Update traces to format text, if necessary
# fig_left.update_traces(texttemplate='%{text:.3s}')  # Using scientific notation for brevity
# # Update layout with title
# fig_left.update_layout(title_text='Amount0 vs Price')

# fig_right = go.Figure(go.Bar(
#     x=right['price'],
#     y=right['amount1'],
#     text=right['amount1'],  # Set bar text
#     textposition='outside'  # Position text outside of bars
# ))
# # Update traces to format text, if necessary
# fig_right.update_traces(texttemplate='%{text:.3s}')  # Using scientific notation for brevity
# # Update layout with title
# fig_right.update_layout(title_text='Amount1 vs Price')

# total_amount0_ = total_amount0 / (10 ** decimals0)
# total_amount1_ = total_amount1 / (10 ** decimals1)
# total_amount_in_token1 = total_amount0_ * current_price + total_amount1_

# c=1