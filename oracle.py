from binance_kline import get_all_kline_data,get_all_kline_future,get_kline_data_from_binance,reverse_price,plot_price_comparison,plot_kline_data,calculate_rolling_beta,plot_dual_axis_time_series_plotly,calculate_rolling_beta_and_correlation,plot_dual_axis_time_series_plotly_three,calculate_rolling_volatility
import pandas as pd
from scipy import spatial

length=24*60+1
start_time='2024-01-01 00:00:00'
#change start time to timestamp
start_time=int(pd.to_datetime(start_time).timestamp()*1000)
symbol='ETHUSDT'
interval='1h'
limit=10000
ethusd=get_all_kline_data(symbol, interval, start_time, endTime=None)
ethusdf=get_all_kline_future(symbol, interval, start_time, endTime=None)
diff=ethusd['Close']-ethusdf['Close']
#plot diff
plot_price_comparison(diff, 'ETHUSDT', 'ETHUSDT_FUTURE').show()

# ethusd=get_kline_data_from_binance(symbol=symbol, interval=interval, limit=limit,startTime=start_time)    
# ethusd=get_kline_data_from_binance('ETHUSDT','1h',500,startTime=start_time)    

ethusd.to_csv('ethusd_120d_1h.csv')
# read the data from the csv file
ethusd = pd.read_csv('ethusd.csv')
#calculate the percentage change in close price of ETHUSDT
ethusd['percentage_change'] = ethusd['Close'].pct_change()
change = ethusd['percentage_change'][1:]
m=1
n=50
observe=4
df_list=[]
time_list=[]
for i in range(0,len(change)-n,m):
    df_list=df_list+[change[i:i+n].tolist()]
    time_list=time_list+[ethusd['Open Time'][i:i+n].tolist()]

# convert df_list to a dataframe


def change_ranked_by_relatedness(
    target,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 3
) -> tuple[list[float], list[float]]:
    change_and_relatednesses = [
        (df, relatedness_fn(target, df))
        for df in df_list
    ]
    # add a new data to the change_and_relatednesses which is the inde of the data
    change_and_relatednesses = [(i, change, relatedness) for i, (change, relatedness) in enumerate(change_and_relatednesses)]
    change_and_relatednesses.sort(key=lambda x: x[2], reverse=True)
    index,change, relatednesses = zip(*change_and_relatednesses)
    return change[:top_n], relatednesses[:top_n],index[:top_n]
# define a fuction to calculate the value start from 1 based on the percent change of a list
def calculate_value(percent_change_list):
    value=[0]*len(percent_change_list)
    value[0]=100
    for i in range(1,len(percent_change_list)):
        value[i]=value[i-1]*(1+percent_change_list[i])
    return value
def getbeck_change(i,change):
    return change[i:i+n+observe].tolist()
target0=get_kline_data_from_binance('ETHUSDC','1h',55)
# target.to_csv('target.csv')
# target0 = pd.read_csv('target.csv')
# plot_kline_data(target0,"ETHUSDT").show()
target0['percentage_change'] = target0['Close'].pct_change()
target = target0['percentage_change'][1:n+1]

change_group = change_ranked_by_relatedness(target, df_list)
top_1=change_group[2][0]
top_2=change_group[2][1]
print(top_1,top_2)

value0=target0['Close'][0:n+observe]/target0['Close'][n]*100
value1=ethusd['Close'][top_1:top_1+n+observe]/ethusd['Close'][top_1+n]*100


value2=ethusd['Close'][top_2:top_2+n+observe]/ethusd['Close'][top_2+n]*100
time1=ethusd['Open Time'][top_1:top_1+n+observe]

# value1=calculate_value(change_group[0][0])
# value2=calculate_value(change_group[0][1])
# value3=calculate_value(change_group[0][2])

#plot value0, value1, value2, value3 in the same plot use plotly
import plotly.graph_objects as go
fig = go.Figure()

fig.add_trace(go.Scatter(x=time1,y=value1, mode='lines', name='value1'))
fig.add_trace(go.Scatter(x=time1,y=value2, mode='lines', name='value2'))
# fig.add_trace(go.Scatter(x=time_list[change_group[2][0]],y=value2, mode='lines', name='value2'))
# fig.add_trace(go.Scatter(x=time_list[change_group[2][0]],y=value3, mode='lines', name='value3'))
fig.add_trace(go.Scatter(x=time1,y=value0, mode='lines', name='value0'))

# Save the plot to an HTML file
plot_file = 'plot.html'
fig.write_html(plot_file)
import webbrowser
import os
# Open the HTML file in the default web browser
webbrowser.open('file://' + os.path.realpath(plot_file))


# #convert the change_group to a dataframe called df which has m columns each column has n data points
# df = pd.DataFrame(change_group).T
# c=1