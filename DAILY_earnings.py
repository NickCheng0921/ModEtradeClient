import os
import datetime
import pandas as pd
import pickle
import numpy as np
import requests
from datetime import datetime, timedelta

import triton_config

mCapMin = 500e6
limit = 500
minGain = 4

DAYS_LOOKAHEAD = 3

df = pd.DataFrame(columns=['Day', 'Date', 'Ticker', 'EWA_Gain', 'STD', 'SR', 'Time'])
os.chdir("/home/nuckchead/Documents/playfair/etrade/")
filename = "dailyDump.csv"
logname = triton_config.MAIN_LOG

def ewa(lst, alpha=0.9):
    n = len(lst)
    ewa = 0
    denominator = 0

    for i in range(n):
        weight = alpha ** (n - i - 1)
        ewa += weight * lst[i]
        denominator += weight

    ewa = ewa / denominator if denominator != 0 else 0
    return (ewa, np.std(lst))

reversion = pd.read_csv('../miscData/meanReversion.csv')

ewa_ticks = None
with open('../miscData/ewa_ticks.pkl', 'rb') as file:
    ewa_ticks = pickle.load(file)

headers = {
    "Accept":"application/json, text/plain, */*",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"en-US,en;q=0.9",
    "Origin":"https://www.nasdaq.com",
    "Referer":"https://www.nasdaq.com",
    "User-Agent":"your user agent..."
}

url = 'https://api.nasdaq.com/api/calendar/earnings?'

def get_earnings_calendar(days_after=1):
    today = datetime.now()
    tomorrow = today + timedelta(days=days_after)
    payload = {"date":tomorrow.strftime('%Y-%m-%d')} 
    source = requests.get( url=url, headers=headers, params=payload, verify=True ) 
    data = source.json()
    return data

for lookahead in range(1, 1+DAYS_LOOKAHEAD):
    today = datetime.now()
    tomorrow = today + timedelta(days=lookahead)
    weekday = tomorrow.strftime('%A')
    ymd = tomorrow.strftime('%Y/%m/%d')

    data = get_earnings_calendar(lookahead)

    filtered_data = []
    if not data['data']['rows']:
        continue

    for d in data['data']['rows']:
        if d['marketCap'] and int(d['marketCap'][1:].replace(',','')) > mCapMin:
            filtered_data.append(d)
    filtered_data = filtered_data[:limit]

    earnings_tickers = [(e['symbol'], e['time']) for e in filtered_data]
    day_earnings = []
    for t, time in earnings_tickers:
        if len([x for x in ewa_ticks if x[2]==t]) > 0:
            day_earnings.append([x+(time,) for x in ewa_ticks if x[2]==t][0])

    day_earnings.sort(reverse=True)
    day_earnings = [d for d in day_earnings if d[0] > minGain]
    for d in day_earnings:
        df.loc[len(df)] = {'Day': weekday, 'Date': ymd, 'Ticker': d[2], 
                           'EWA_Gain': round(d[0], 2), 'STD': round(d[3], 2), 
                           'SR': round(d[0]/d[3], 3), 'Time': d[4]}

df.sort_values(by='SR', inplace=True, ascending=False)
df.to_csv(filename, index=False)
df.to_csv('dailyDump'+today.strftime('%Y-%m-%d')+'.csv', index=False)

with open(logname, "a+") as file:
    file.write(f"Earnings scrape  {datetime.now()}\n\n")
