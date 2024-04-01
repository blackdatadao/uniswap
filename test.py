import time,requests,json
import pandas as pd

url='http://42.192.17.155/nft_list'
response = requests.get(url)
assert response.status_code==200
nfts_list=response.json()
nft_list=pd.DataFrame(nfts_list)
id=50689
print(nft_list['nft_id'])

if id not in nft_list['nft_id'].values:
    print('id not in nft_list')
    exit()
else:
    print('id in nft_list')


c=1