import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import os
import yfinance as yf

import triton_config

BASKET_SIZE = 5
STOP_LOSS = 4 # percent below spot
TARGET_GAIN = .9 # of expected gain

FILENAME = triton_config.ORDER_FILE_NAME
logname = triton_config.MAIN_LOG

def main(UNDERLYING = 0, sandbox = True):
    os.chdir("/home/nuckchead/Documents/playfair/etrade/")
    df = pd.read_csv("./dailyDump.csv")
    df.sort_values(by='SR', inplace=True, ascending=False)

    today = datetime.now()
    tomorrow = (today + timedelta(days=1)).strftime('%Y/%m/%d')

    #day = today.strftime('%A')
    #if day in ['Saturday', 'Sunday']:
    #    print("Not a trading day")
    #    return []

    tickers = []
    share_prices = []
    gains = []

    for _, row in df[:BASKET_SIZE].iterrows():
        if tomorrow == row['Date']:
            ticker = row["Ticker"]

            tick_df = yf.download(ticker, period="1d")
            if not len(tick_df):
                continue
            
            tickers.append(ticker)
            share_prices.append(list(tick_df['Close'])[0])
            gains.append(row["EWA_Gain"])

    underlying_split = UNDERLYING / BASKET_SIZE

    multiples = [int(underlying_split/sp) for sp in share_prices]

    orders = []
    with open(FILENAME, "w") as file:
        file.write(f"{(today).strftime('%Y/%m/%d')} BUY_AT_CLOSE\n")
        for t, m, sp, g in zip(tickers, multiples, share_prices, gains):
            file.write(f"{t} {m} {round(sp, 2)} {round(g, 2)}\n")
            if m > 0:
                orders.append((t, m))

    with open(logname, "a+") as file:
        file.write(f"Order generation {datetime.now()}")
        if sandbox:
            file.write(f" SANDBOX\n")
        else:
            file.write(f" PROD\n")
            
        for t, m, sp, g in zip(tickers, multiples, share_prices, gains):
                file.write(f"   {t} {m} {round(sp, 2)} {round(g, 2)}\n")
        file.write("\n")

    return orders
