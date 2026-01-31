import pandas as pd


def calculate_kijun(history, kijun_period):
    kijun = {}

    for i in range(kijun_period, len(history)):
        dt = pd.to_datetime(history[i]["Date"])
        kijun_value = 0
        highestBidHigh = -100000
        lowestBidLow = 100000
        for j in range(i-kijun_period, i):
            highestBidHigh = history[j]["BidHigh"] if history[j]["BidHigh"] > highestBidHigh else highestBidHigh
            lowestBidLow = history[j]["BidLow"] if history[j]["BidLow"] < lowestBidLow else lowestBidLow

        kijun_value =  (highestBidHigh + lowestBidLow) / 2
        kijun[dt] = kijun_value

    return kijun
