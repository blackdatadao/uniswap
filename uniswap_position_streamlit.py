#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

c=1

import pandas as pd
import streamlit as st

nft_data=pd.read_csv('nft_data_open.csv')

df3=nft_data[['nft_id','symbol0','symbol1','tick_lower','tick_upper','current_fee0','current_fee1','withdrawable_token0','withdrawable_token1','created_time','create_token0','create_token1','duration']]

# st.table(df3)
