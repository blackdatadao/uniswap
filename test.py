import time,requests,json
import pandas as pd

url='http://42.192.17.155/realised_id'
response = requests.get(url)
assert response.status_code==200
nfts_list=response.json()
id=50689

if id not in nfts_list.values:
    print('id not in nft_list')
    exit()
else:
    print('id in nft_list')


c=1