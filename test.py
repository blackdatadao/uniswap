import time
def timestamp_to_time(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp))

print('0x'+hex(1264785)[2:].rjust(64,'0'))
print(timestamp_to_time(1711634236))