import os
import pandas as pd
import math
import sys
import certifi
import ssl
from ssl import SSLContext

from datetime import datetime, timedelta, time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from db_utils import update_trade_stoploss, update_trade_closed, get_partial_trade, update_trade_in_progress,close_trade_in_retest, upsert_order_waiting_retest, close_mt5_orders_already_processed, update_trade_target, update_trade_target_ALL, get_partial_trade_closed, close_mt5_partial_positions, fetch_trades_from_db, fetch_trades_from_mt5, mt5_place_order, mt5_close_order, mt5_close_positions, SIMULATION_MODE, log_mt5_signal

# Import condizionale di MetaTrader5
if not SIMULATION_MODE:
    import MetaTrader5 as mt5
else:
    mt5 = None


def format_history(hist, timeframe):
    history = [] 
    date_format = '%m.%d.%Y %H:%M:%S'

    #poichè i dati provengono da FXCM nel timeframe DLY rimuoviamo i sabati per far corrispondere i 
    #risultati con ciò che mostra tradingViews
    if timeframe == 'DLY':
        for row in hist:
            formatted_date = pd.to_datetime(str(row['Date']))
            if formatted_date.weekday() != 5:
                formatted_date_str = formatted_date.strftime(date_format)
                history.append({'Date': formatted_date_str, 'BidOpen': row['BidOpen'], 'BidHigh': row['BidHigh'], 'BidLow': row['BidLow'], 'BidClose': row['BidClose'], 'Volume': row['Volume']})
    else:
        for row in hist:
            formatted_date = pd.to_datetime(str(row['Date'])).strftime(date_format)
            history.append({'Date': formatted_date, 'BidOpen': row['BidOpen'], 'BidHigh': row['BidHigh'], 'BidLow': row['BidLow'], 'BidClose': row['BidClose'], 'Volume': row['Volume']})
        

    return history

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

def get_last_hour(kijun_h4, date_str):
    target_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()
    last_hour = None
    last_hour_exception = None
    for hour in kijun_h4.keys():
        
        # only for the 21:00:00 exception
        if hour.date() == target_date - timedelta(days=1):
            last_hour_exception = hour

        if hour.date() == target_date:
            last_hour = hour

    if last_hour is None:
        last_hour = last_hour_exception

    return last_hour 

def get_first_hour(kijun_h4, date_str):
    target_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()
    first_hour = None
    for hour in sorted(kijun_h4.keys()):
        if hour.date() == target_date:
            first_hour = hour
            break
    return first_hour

def get_index_of_first_h4_candle_on_date(history_H4, target_date_str):
    dt = pd.to_datetime(target_date_str)
    target_date = dt.strftime('%Y-%m-%d %H:%M:%S')
    target_date = datetime.strptime(target_date, '%Y-%m-%d %H:%M:%S')
    #target_date = datetime.strptime(target_date_str, '%Y-%m-%d %H:%M:%S')
    for i, candle in enumerate(history_H4):
        candle_datetime = pd.to_datetime(candle['Date'])
        candle_datetime = candle_datetime.strftime('%Y-%m-%d %H:%M:%S')
        candle_datetime = datetime.strptime(candle_datetime, '%Y-%m-%d %H:%M:%S')
        if candle_datetime.date() == target_date.date():
            return i
    return -1  # Return -1 if no candle is found on the target date

def get_index_of_last_h4_candle_on_daily_date(history_H4, target_date_str, session, date_to):
    if session == 'Trade':
        print('target_date_str: '+str(target_date_str))
    dt = pd.to_datetime(target_date_str)
    # Current date and time
    now = datetime.now().time()
    
    
    # Define the time range
    start_time = time(21, 0, 0)
    end_time = time(1, 0, 0)
    if session == 'Trade':
        print('now: '+str(now))
        print('start_time: '+str(start_time))
        print('end_time: '+str(end_time))
    # If current time is not between 21:00:00 and 01:00:00 of the next day
    if not ((now >= start_time) or (now <= end_time)):
        print(str(now >= start_time))
        print(str(now <= end_time))
        # Add one day to the target date
        dt += timedelta(days=1)

    print('dt: '+str(dt))
    print('history h4: '+str(history_H4[-1]))
    
    #input()
    target_date = dt.strftime('%Y-%m-%d %H:%M:%S')
    target_date = datetime.strptime(target_date, '%Y-%m-%d %H:%M:%S')
    last_index = -1
    for i, candle in enumerate(history_H4):
        candle_datetime = pd.to_datetime(candle['Date'])
        candle_datetime = candle_datetime.strftime('%Y-%m-%d %H:%M:%S')
        candle_datetime = datetime.strptime(candle_datetime, '%Y-%m-%d %H:%M:%S')
        #print(str(candle_datetime.date())+' - '+str(target_date.date()))
        if candle_datetime.date() == target_date.date():
            last_index = i
    return last_index  # Return -1 if no candle is found on the target date

def get_zones(history, kijun_h4, index, timerange, type, dlyZoneDate):

    lastclosearray = []
    zones_rectX1 = []
    zones_rectX2 = []
    zones_rectY1 = []
    zones_rectY2 = []
    final_zones =  []
    zone = 0
    zone_type = None

    dt = pd.to_datetime(history[index]["Date"])
   
    # Add one day to the datetime object to adjust the history daily error
    if timerange == 'DLY': # and type == 'Trade' :
        dt = dt + timedelta(days=1)
        #print('#### start the day: '+ str(dt))

    dt_str = get_last_hour(kijun_h4, dt.strftime('%Y-%m-%d %H:%M:%S'))
    
    #print('- kijun h4 candle date: '+ str(dt_str))
    #print('- kijun h4 candle value: '+str(kijun_h4[dt_str]))
    if type == 'BTLOG':
        print('i: '+str(index))
    if dt_str in kijun_h4 and history[index]["BidClose"] < kijun_h4[dt_str]: 
            zone_type = 'SUP'           
            lastclosearray.clear()
            zones_rectX1.clear()
            zones_rectX2.clear()
            zones_rectY1.clear()
            zones_rectY2.clear()

            rectY2 = 0

            zone_datetime = datetime.strptime(history[index-1]['Date'], '%m.%d.%Y %H:%M:%S')
            zone_date = zone_datetime.date()
            #zone_last_date = zone_date.replace(year=zone_date.year - 1)
            try:
                # Your existing code to manipulate zone_date
                zone_last_date = zone_date.replace(year=zone_date.year - 1)
            except ValueError:
                # Check if it's a leap day
                if zone_date.month == 2 and zone_date.day == 29:
                    # Adjust the day for non-leap year
                    zone_last_date = zone_date.replace(year=zone_date.year - 1, day=28)
                else:
                    raise  # Re-raise the original exception if it's not the leap day case

            for i in range(index-1, -1, -1):

                # Convert the string to a datetime object
                history_date_datetime = datetime.strptime(history[i]['Date'], '%m.%d.%Y %H:%M:%S')
                
                # Extract just the date part from the datetime objects
                history_date_date = history_date_datetime.date()

                #print('history_date_datetime: '+str(history_date_datetime))
                #print('dlyZoneDate_datetime: '+str(dlyZoneDate_datetime))

                if history_date_date < zone_last_date:
                    break

                lastclosearray.append(history[i]['BidClose'])
                minlow = min(history[i]['BidLow'], history[i+1]['BidLow'])

                if history[i]['BidOpen'] > history[i]['BidClose'] and history[i+1]['BidOpen'] < history[i+1]['BidClose']:
                    
                    if history[i-1]['BidOpen'] > history[i-1]['BidClose']:
                        minlow = min(history[i-1]['BidLow'], history[i]['BidLow'], history[i+1]['BidLow'])
                
                    if minlow < min(lastclosearray) or minlow < rectY2:
                        rectX1 = history[i+1]["Date"] #add 1 due to an error date on history daily
                        rectX2 = i
                        rectY1 = minlow
                        rectY2 = history[i]['BidClose'] 

                        zones_rectX1.append(rectX1)
                        zones_rectX2.append(rectX2)
                        zones_rectY1.append(rectY1)
                        zones_rectY2.append(rectY2)

            zones_rectX1.reverse()
            zones_rectX2.reverse()
            zones_rectY1.reverse()
            zones_rectY2.reverse()

            final_zones.clear()
            zone = 0
            
            for i in range(len(zones_rectY2)):
                #print('final_zones: '+str(final_zones))
                #print('zone: '+str(zone))

                if i == len(zones_rectY2)-1:
                    if zone not in final_zones:
                        final_zones.append(zone)
                    break

                if zones_rectY2[i+1] < zones_rectY1[zone]:
                    zone = i+1
                    while len(final_zones) > 0:
                        z = final_zones.pop()
                        if zones_rectY2[z] < zones_rectY1[i+1]:
                            final_zones.append(z)
                            zone = i+1
                            break
                        elif zones_rectY1[i+1] > zones_rectY2[z]:
                            zone = i+1
                        elif zones_rectY2[i+1] > zones_rectY2[z] and zones_rectY1[i+1] < zones_rectY1[z]:
                            zone = z
                            break
                        elif zones_rectY2[i+1] > zones_rectY1[z] and zones_rectY2[i+1] < zones_rectY2[z]:
                            zone = z
                            break
                        elif zones_rectY1[i+1] > zones_rectY1[z] and zones_rectY1[i+1] < zones_rectY2[z]:
                            zone = z
                            break
                elif zones_rectY1[i+1] > zones_rectY2[zone]:
                    final_zones.append(zone)
                    zone = i+1 
    elif dt_str in kijun_h4 and history[index]["BidClose"] > kijun_h4[dt_str]:
            zone_type = 'RES' 
            zones_rectX1, zones_rectX2, zones_rectY1, zones_rectY2, final_zones = get_resistences(history, index, type, timerange, dlyZoneDate)

    return zones_rectX1, zones_rectX2, zones_rectY1, zones_rectY2, final_zones, zone_type

def get_resistences(history, index, session, timerange, dlyZoneDate):

    lastclosearray = []
    zones_rectX1 = []
    zones_rectX2 = []
    zones_rectY1 = []
    zones_rectY2 = []
    final_zones =  []
    zone = 0
    rectY2 = 0

    zone_datetime = datetime.strptime(history[index-1]['Date'], '%m.%d.%Y %H:%M:%S')
    zone_date = zone_datetime.date()
    #zone_last_date = zone_date.replace(year=zone_date.year - 1)

    try:
        # Your existing code to manipulate zone_date
        zone_last_date = zone_date.replace(year=zone_date.year - 1)
    except ValueError:
        # Check if it's a leap day
        if zone_date.month == 2 and zone_date.day == 29:
            # Adjust the day for non-leap year
            zone_last_date = zone_date.replace(year=zone_date.year - 1, day=28)
        else:
            raise  # Re-raise the original exception if it's not the leap day case

    for i in range(index-1, -1, -1):

        # Convert the string to a datetime object
        history_date_datetime = datetime.strptime(history[i]['Date'], '%m.%d.%Y %H:%M:%S')
        
        # Extract just the date part from the datetime objects
        history_date_date = history_date_datetime.date()

        #print('history_date_datetime: '+str(history_date_datetime))
        #print('dlyZoneDate_datetime: '+str(dlyZoneDate_datetime))

        if history_date_date < zone_last_date:
            break

        lastclosearray.append(history[i]['BidClose'])
        maxhigh = max(history[i]['BidHigh'], history[i+1]['BidHigh'])

        if history[i]['BidOpen'] < history[i]['BidClose'] and history[i+1]['BidOpen'] > history[i+1]['BidClose']:
            
            if history[i-1]['BidOpen'] < history[i-1]['BidClose']:
                maxhigh = max(history[i-1]['BidHigh'], history[i]['BidHigh'], history[i+1]['BidHigh'])
        
            if maxhigh > max(lastclosearray) or maxhigh > rectY2:
                rectX1 = history[i+1]["Date"] #add 1 due to an error date on history daily
                rectX2 = i
                rectY1 = maxhigh
                rectY2 = history[i]['BidClose'] 

                zones_rectX1.append(rectX1)
                zones_rectX2.append(rectX2)
                zones_rectY1.append(rectY1)
                zones_rectY2.append(rectY2)

    zones_rectX1.reverse()
    zones_rectX2.reverse()
    zones_rectY1.reverse()
    zones_rectY2.reverse()

    if session == 'BTLOG':
        print('zones_rectX1 before: '+str(zones_rectX1))
        input()
    
    

    final_zones.clear()
    zone = 0
    for i in range(len(zones_rectY2)):
        #print('final_zones: '+str(final_zones))
        #print('zone: '+str(zone))

        if i == len(zones_rectY2)-1:
            if zone not in final_zones:
                final_zones.append(zone)
            break

        if zones_rectY2[i+1] > zones_rectY1[zone]:
            zone = i+1
            while len(final_zones) > 0:
                z = final_zones.pop()
                if zones_rectY2[z] > zones_rectY1[i+1]:
                    final_zones.append(z)
                    zone = i+1
                    break
                elif zones_rectY1[z] < zones_rectY2[i+1]:
                    zone = i+1
                elif zones_rectY1[i+1] > zones_rectY1[z] and zones_rectY2[i+1] < zones_rectY2[z]:
                    zone = z
                    break
                elif zones_rectY1[i+1] < zones_rectY1[z] and zones_rectY1[i+1] > zones_rectY2[z]:
                    zone = z
                    break
                elif zones_rectY2[i+1] < zones_rectY1[z] and zones_rectY2[i+1] > zones_rectY2[z]:
                    zone = z
                    break
        elif zones_rectY1[i+1] < zones_rectY2[zone]:
            final_zones.append(zone)
            zone = i+1 

    if session == 'BTLOG':
        print('zones_rectX1: '+str(zones_rectX1))
        input()
   
    return zones_rectX1, zones_rectX2, zones_rectY1, zones_rectY2, final_zones

def send_slack_message(channel, message):

    env_path = ".env"
    load_dotenv(env_path)

    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    sslcert = SSLContext()
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'], ssl=sslcert)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )
        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e}")

# Function to open a trade
def place_order(symbol, lot, price, sl_points, tp_points, order_type):
    # SIMULATION MODE
    if SIMULATION_MODE:
        # Simula point value
        if 'JPY' in symbol:
            point = 0.001
        else:
            point = 0.00001
        
        sl = price - sl_points * point
        tp = price + tp_points * point
        order_type_str = str(order_type) if order_type else 'UNKNOWN'
        
        log_mt5_signal(
            signal_type='PLACE_ORDER_DIRECT',
            pair=symbol[:3] + '/' + symbol[3:] if len(symbol) == 6 else symbol,
            action='PENDING',
            order_type=order_type_str,
            volume=lot,
            price=price,
            stop_loss=sl,
            take_profit=tp,
            deviation=20,
            comment='python script open'
        )
        print(f"[SIMULATION] place_order: {symbol} @ {price}, SL: {sl}, TP: {tp}")
        return True
    
    # PRODUCTION MODE
    point = mt5.symbol_info(symbol).point
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": price - sl_points * point,
        "tp": price + tp_points * point,
        "deviation": 20,
        "magic": 234000,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("order_send failed, retcode={}".format(result.retcode))
        result_dict = result._asdict()
        for field in result_dict.keys():
            print("   {}={}".format(field,result_dict[field]))
        return False

    return True

def validate_resistence(zone_rectX1, zones_rectX2, zones_rectY1, zones_rectY2, history, timeframe, kijun_h4,str_instrument, type):
    
    zone_validated = False
    last_candle = []
    anchor = None

    start_index = zones_rectX2
    zone_valid = False
    zone_touch = False

    for i, candle in enumerate(history[start_index+1:]):
        #print('timeframe: '+str(timeframe)+' - zone: '+str(zone_rectX1)+' - (zone_touch: '+str(zone_touch)+'- (time: '+str(candle["Date"]))
        dt = pd.to_datetime(candle["Date"])
        
        if timeframe == 'DLY':  
            dt_str = get_last_hour(kijun_h4, dt.strftime('%Y-%m-%d %H:%M:%S'))
        elif timeframe == 'H4': 
            dt_str = dt
            
        if candle['BidClose'] > zones_rectY1 and candle != history[-1]:
            last_candle = candle
            zone_validated = False
            break
        
        if zone_valid == True:
            if candle['BidHigh'] >= zones_rectY2:
                if zone_touch == False:
                    anchor = candle['Date']
                zone_touch = True
                last_candle = candle
                zone_validated = True
            
            elif dt_str in kijun_h4 and candle['BidLow'] <= kijun_h4[dt_str]: 
                zone_touch = False
                zone_validated = False
        
        elif zone_valid == False:
            if dt_str in kijun_h4 and candle['BidLow'] < kijun_h4[dt_str]: 
                zone_valid = True
                #print('zone_valid: '+str(candle['Date']))
                if candle['BidHigh'] >= zones_rectY2 and candle['Date'] != history[start_index+1]['Date']:
                    zone_touch = True
                    last_candle = candle
                    zone_validated = True
                    anchor = candle['Date']
    
    return last_candle, zone_valid, zone_validated, anchor

def validate_support(zone_rectX1, zones_rectX2, zones_rectY1, zones_rectY2, history, timeframe, kijun_h4,str_instrument, type):
    
    zone_validated = False
    last_candle = []
    anchor = None
    
    start_index = zones_rectX2
    zone_valid = False
    zone_touch = False

    for candle in history[start_index+1:]:
        dt = pd.to_datetime(candle["Date"]) 
            
        if timeframe == 'DLY':  
            dt_str = get_last_hour(kijun_h4, dt.strftime('%Y-%m-%d %H:%M:%S'))
        elif timeframe == 'H4': 
            dt_str = dt
        
        if candle['BidClose'] < zones_rectY1 and candle != history[-1]:
                last_candle = candle
                zone_validated = False
                break

        if zone_valid == True:
            if candle['BidLow'] <= zones_rectY2:
                if zone_touch == False:
                    anchor = candle['Date']
                zone_touch = True
                last_candle = candle
                zone_validated = True
            elif dt_str in kijun_h4 and candle['BidHigh'] > kijun_h4[dt_str]: 
                zone_touch = False
                zone_validated = False
        
        elif zone_valid == False:
            if dt_str in kijun_h4 and candle['BidHigh'] > kijun_h4[dt_str]: 
                zone_valid = True
                #print('zone_valid: '+str(candle['Date']))
                if candle['BidLow'] <= zones_rectY2 and candle['Date'] != history[start_index+1]['Date']:
                    zone_touch = True
                    last_candle = candle
                    zone_validated = True
                    anchor = candle['Date']

    return last_candle, zone_valid, zone_validated, anchor

def get_pattern_m15_SUP(history,kijun_h4, zone_rectX1_h4, zone_rectX2_h4, zone_rectY1_h4, zone_rectY2_h4,str_instrument,str_session):

    rectX1 = None
    rectX2 = None
    rectY1 = None
    rectY2 = None

    lastlow = history[-1]["BidLow"]
    left_lastlow_higher_closure = history[-1]["BidClose"]
    lowestclose = history[-1]["BidClose"]

    if history[-1]['BidClose'] < list(kijun_h4.values())[-1]:  
        patterns_left_rectX1 = []
        patterns_left_rectX2 = []
        patterns_left_rectY1 = []
        patterns_left_rectY2 = []

        patterns_right_rectX1 = []
        patterns_right_rectX2 = []
        patterns_right_rectY1 = []
        patterns_right_rectY2 = []

        for i in range(len(history)-1, -1, -1):
            
            if history[i]["Date"] == zone_rectX1_h4:
                if str_session == 'Trade':  
                    ('The search for the pattern is stopped because the beginning of the valid h4 zone has been reached: '+history[i]["Date"])
                break
            
            nearest_kijun_val = get_nearest_lower_kijun_h4(history[i], kijun_h4)
            if history[i]["BidHigh"] >= nearest_kijun_val:
                if str_session == 'Trade':
                    print('- The search for the pattern is stopped because the BidHigh is above the kijun h4: '+history[i]["Date"])
                break

            #if left_lastlow_higher_closure < history[i]["BidClose"]:
                #left_lastlow_higher_closure = history[i]["BidClose"]
            
            if lowestclose > history[i]["BidLow"]:
                
                # Initialize lastlow with the current item's BidLow
                lastlow = history[i]['BidLow']

                # If not at the start of the list, compare with the previous item's BidLow
                if i > 0:
                    lastlow = min(lastlow, history[i-1]['BidLow'])

                # If not at the end of the list, compare with the next item's BidLow
                if i < len(history) - 1:
                    lastlow = min(lastlow, history[i+1]['BidLow'])
                    
                lowestclose = history[i]["BidClose"]
           
                #left_lastlow_higher_closure = history[i]["BidClose"]
                for j in range(len(patterns_left_rectY1)):
                    patterns_right_rectX1.append(patterns_left_rectX1[j])
                    patterns_right_rectX2.append(patterns_left_rectX2[j])
                    patterns_right_rectY1.append(patterns_left_rectY1[j])
                    patterns_right_rectY2.append(patterns_left_rectY2[j])
                patterns_left_rectX1.clear()
                patterns_left_rectX2.clear()
                patterns_left_rectY1.clear()
                patterns_left_rectY2.clear()

            # due candele + due candele
            if (history[i]["BidOpen"] > history[i]["BidClose"] and 
                history[i-1]["BidOpen"] > history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] < history[i-2]["BidClose"] and 
                history[i-3]["BidOpen"] < history[i-3]["BidClose"]):
                
                #if max(history[i-2]["BidHigh"], history[i-1]["BidHigh"]) >= left_lastlow_higher_closure:
                    # Define the coordinates of the rectangle
                patterns_left_rectX1.append(history[i-2]["Date"]) 
                patterns_left_rectX2.append(i-2)
                patterns_left_rectY1.append(max(history[i-2]["BidHigh"], history[i-1]["BidHigh"]))
                patterns_left_rectY2.append(history[i-2]["BidClose"])
                continue

            # engulfing + due candele 
            if (history[i]["BidOpen"] > history[i]["BidClose"] and 
                history[i-1]["BidOpen"] > history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] < history[i-2]["BidClose"] and 
                history[i-3]["BidOpen"] > history[i-3]["BidClose"] and
                history[i-2]["BidClose"] > history[i-3]["BidHigh"]):
                
                #if max(history[i-2]["BidHigh"], history[i-1]["BidHigh"]) >= left_lastlow_higher_closure:
                patterns_left_rectX1.append(history[i-2]["Date"]) 
                patterns_left_rectX2.append(i-2)
                patterns_left_rectY1.append(max(history[i-2]["BidHigh"], history[i-1]["BidHigh"]))
                patterns_left_rectY2.append(history[i-2]["BidClose"])
                continue

            # engulfing + engulfing
            if (history[i]["BidOpen"] > history[i]["BidClose"] and 
                history[i-1]["BidOpen"] < history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] > history[i-2]["BidClose"] and 
                history[i-1]["BidClose"] > history[i-2]["BidHigh"] and
                history[i]["BidClose"] < history[i-1]["BidLow"]):
                
                #if max(history[i-1]["BidHigh"], history[i]["BidHigh"]) >= left_lastlow_higher_closure:
                patterns_left_rectX1.append(history[i-1]["Date"]) 
                patterns_left_rectX2.append(i-1)
                patterns_left_rectY1.append(max(history[i-1]["BidHigh"], history[i]["BidHigh"]))
                patterns_left_rectY2.append(history[i-1]["BidClose"])
                continue

            # due candele + enfulfing
            if (history[i]["BidOpen"] > history[i]["BidClose"] and 
                history[i-1]["BidOpen"] < history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] < history[i-2]["BidClose"] and 
                history[i]["BidClose"] < history[i-1]["BidLow"]):

                #if max(history[i-1]["BidHigh"], history[i]["BidHigh"]) >= left_lastlow_higher_closure:
                patterns_left_rectX1.append(history[i-1]["Date"]) 
                patterns_left_rectX2.append(i-1)
                patterns_left_rectY1.append(max(history[i-1]["BidHigh"], history[i]["BidHigh"]))
                patterns_left_rectY2.append(history[i-1]["BidClose"])
                continue

        rectX1_sx = None if len(patterns_left_rectX1) == 0 else patterns_left_rectX1[0]
        rectX2_sx = None if len(patterns_left_rectX2) == 0 else patterns_left_rectX2[0]
        rectY1_sx = None if len(patterns_left_rectY1) == 0 else patterns_left_rectY1[0]
        rectY2_sx = None if len(patterns_left_rectY2) == 0 else patterns_left_rectY2[0]

        rectX1_dx = None if len(patterns_right_rectX1) == 0 else patterns_right_rectX1[-1]
        rectX2_dx = None if len(patterns_right_rectX2) == 0 else patterns_right_rectX2[-1]
        rectY1_dx = None if len(patterns_right_rectY1) == 0 else patterns_right_rectY1[-1]
        rectY2_dx = None if len(patterns_right_rectY2) == 0 else patterns_right_rectY2[-1]
        
        if rectY1_sx is None and rectY1_dx is not None:
            rectX1 = rectX1_dx
            rectX2 = rectX2_dx
            rectY1 = rectY1_dx
            rectY2 = rectY2_dx
        elif rectY1_dx is None and rectY1_sx is not None:
            rectX1 = rectX1_sx
            rectX2 = rectX2_sx
            rectY1 = rectY1_sx
            rectY2 = rectY2_sx
        elif rectY1_dx is not None and rectY1_sx is not None:
            if rectY2_sx > rectY1_dx:
                rectX1 = rectX1_dx
                rectX2 = rectX2_dx
                rectY1 = rectY1_dx
                rectY2 = rectY2_dx
            else:
                rectX1 = rectX1_sx
                rectX2 = rectX2_sx
                rectY1 = rectY1_sx
                rectY2 = rectY2_sx

    #if rectX1 is not None:
        #send_slack_message('general',':ballot_box_with_check: In attesa rottura o retest pattern: '+str_instrument)
    return rectX1, rectX2, rectY1,rectY2, lastlow

def get_pattern_m15_RES(history,kijun_h4, zone_rectX1_h4, zone_rectX2_h4, zone_rectY1_h4, zone_rectY2_h4,str_instrument,str_session):

    rectX1 = None
    rectX2 = None
    rectY1 = None
    rectY2 = None

    lasthigh = history[-1]["BidHigh"]
    highestclose = history[-1]["BidClose"]
    
    left_lasthigh_lower_closure = history[-1]["BidClose"]
    if str_session == 'Trade':
        print('first lasthigh: '+str(lasthigh)+' - Date: '+str(history[-1]["Date"])) 

    if history[-1]['BidClose'] > list(kijun_h4.values())[-1]:  
        patterns_left_rectX1 = []
        patterns_left_rectX2 = []
        patterns_left_rectY1 = []
        patterns_left_rectY2 = []

        patterns_right_rectX1 = []
        patterns_right_rectX2 = []
        patterns_right_rectY1 = []
        patterns_right_rectY2 = []

        for i in range(len(history)-1, -1, -1):
            
            if history[i]["Date"] == zone_rectX1_h4:
                if str_session == 'Trade':
                    print('The search for the pattern is stopped because the beginning of the valid h4 zone has been reached: '+history[i]["Date"])
                break
            
            nearest_kijun_val = get_nearest_lower_kijun_h4(history[i], kijun_h4)
            if history[i]["BidLow"] <= nearest_kijun_val:
                if str_session == 'Trade':
                    print('- The search for the pattern is stopped because the BidLow is below the kijun h4: '+history[i]["Date"])
                break

            #if left_lasthigh_lower_closure > history[i]["BidClose"]:
                #left_lasthigh_lower_closure = history[i]["BidClose"]

            if highestclose < history[i]["BidHigh"]:
                # Initialize lasthigh with the current item's BidHigh
                lasthigh = history[i]['BidHigh']

                # If not at the start of the list (remember we're iterating in reverse), compare with the next item's BidHigh
                if i < len(history) - 1:
                    lasthigh = max(lasthigh, history[i+1]['BidHigh']) 

                # If not at the end of the list, compare with the previous item's BidHigh
                if i > 0:
                    lasthigh = max(lasthigh, history[i-1]['BidHigh'])

                highestclose = history[i]["BidClose"]

                #left_lasthigh_lower_closure = history[i]["BidClose"]
                for j in range(len(patterns_left_rectY1)):
                    patterns_right_rectX1.append(patterns_left_rectX1[j])
                    patterns_right_rectX2.append(patterns_left_rectX2[j])
                    patterns_right_rectY1.append(patterns_left_rectY1[j])
                    patterns_right_rectY2.append(patterns_left_rectY2[j])
                patterns_left_rectX1.clear()
                patterns_left_rectX2.clear()
                patterns_left_rectY1.clear()
                patterns_left_rectY2.clear()

            # due candele + due candele
            if (history[i]["BidOpen"] < history[i]["BidClose"] and 
                history[i-1]["BidOpen"] < history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] > history[i-2]["BidClose"] and 
                history[i-3]["BidOpen"] > history[i-3]["BidClose"]):

                #if min(history[i-2]["BidLow"], history[i-1]["BidLow"]) <= left_lasthigh_lower_closure:                
                    # Define the coordinates of the rectangle
                patterns_left_rectX1.append(history[i-2]["Date"]) 
                patterns_left_rectX2.append(i-2)
                patterns_left_rectY1.append(min(history[i-2]["BidLow"], history[i-1]["BidLow"]))
                patterns_left_rectY2.append(history[i-2]["BidClose"])
                continue

            # engulfing + due candele 
            if (history[i]["BidOpen"] < history[i]["BidClose"] and 
                history[i-1]["BidOpen"] < history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] > history[i-2]["BidClose"] and 
                history[i-3]["BidOpen"] < history[i-3]["BidClose"] and
                history[i-2]["BidClose"] < history[i-3]["BidLow"]):
                
                #if min(history[i-2]["BidLow"], history[i-1]["BidLow"]) <= left_lasthigh_lower_closure:        
                patterns_left_rectX1.append(history[i-2]["Date"]) 
                patterns_left_rectX2.append(i-2)
                patterns_left_rectY1.append(min(history[i-2]["BidLow"], history[i-1]["BidLow"]))
                patterns_left_rectY2.append(history[i-2]["BidClose"])
                continue

            # engulfing + engulfing
            if (history[i]["BidOpen"] < history[i]["BidClose"] and 
                history[i-1]["BidOpen"] > history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] < history[i-2]["BidClose"] and 
                history[i-1]["BidClose"] < history[i-2]["BidLow"] and
                history[i]["BidClose"] > history[i-1]["BidHigh"]):
                
                #if min(history[i-1]["BidLow"], history[i]["BidLow"]) <= left_lasthigh_lower_closure:        
                patterns_left_rectX1.append(history[i-1]["Date"]) 
                patterns_left_rectX2.append(i-1)
                patterns_left_rectY1.append(min(history[i-1]["BidLow"], history[i]["BidLow"]))
                patterns_left_rectY2.append(history[i-1]["BidClose"])
                continue

            # due candele + enfulfing
            if (history[i]["BidOpen"] < history[i]["BidClose"] and 
                history[i-1]["BidOpen"] > history[i-1]["BidClose"] and 
                history[i-2]["BidOpen"] > history[i-2]["BidClose"] and 
                history[i]["BidClose"] > history[i-1]["BidHigh"]):

                #if min(history[i-1]["BidLow"], history[i]["BidLow"]) <= left_lasthigh_lower_closure:        
                patterns_left_rectX1.append(history[i-1]["Date"]) 
                patterns_left_rectX2.append(i-1)
                patterns_left_rectY1.append(min(history[i-1]["BidLow"], history[i]["BidLow"]))
                patterns_left_rectY2.append(history[i-1]["BidClose"])
                continue

        rectX1_sx = None if len(patterns_left_rectX1) == 0 else patterns_left_rectX1[0]
        rectX2_sx = None if len(patterns_left_rectX2) == 0 else patterns_left_rectX2[0]
        rectY1_sx = None if len(patterns_left_rectY1) == 0 else patterns_left_rectY1[0]
        rectY2_sx = None if len(patterns_left_rectY2) == 0 else patterns_left_rectY2[0]

        rectX1_dx = None if len(patterns_right_rectX1) == 0 else patterns_right_rectX1[-1]
        rectX2_dx = None if len(patterns_right_rectX2) == 0 else patterns_right_rectX2[-1]
        rectY1_dx = None if len(patterns_right_rectY1) == 0 else patterns_right_rectY1[-1]
        rectY2_dx = None if len(patterns_right_rectY2) == 0 else patterns_right_rectY2[-1]
        
        if rectY1_sx is None and rectY1_dx is not None:
            rectX1 = rectX1_dx
            rectX2 = rectX2_dx
            rectY1 = rectY1_dx
            rectY2 = rectY2_dx
        elif rectY1_dx is None and rectY1_sx is not None:
            rectX1 = rectX1_sx
            rectX2 = rectX2_sx
            rectY1 = rectY1_sx 
            rectY2 = rectY2_sx
        elif rectY1_dx is not None and rectY1_sx is not None:
            if rectY2_sx < rectY1_dx:
                rectX1 = rectX1_dx
                rectX2 = rectX2_dx
                rectY1 = rectY1_dx
                rectY2 = rectY2_dx
            else:
                rectX1 = rectX1_sx
                rectX2 = rectX2_sx
                rectY1 = rectY1_sx
                rectY2 = rectY2_sx

    #if rectX1 is not None:
        #send_slack_message('general',':ballot_box_with_check: In attesa rottura o retest pattern: '+str_instrument)
    return rectX1, rectX2, rectY1,rectY2, lasthigh
             
def get_nearest_lower_kijun_h4(candle_15_min, kijun_h4):

    target_date = datetime.strptime(candle_15_min["Date"], '%m.%d.%Y %H:%M:%S').date()
    times = [time(1, 0), time(5, 0), time(9, 0), time(13, 0), time(17, 0), time(21, 0)]
    
    # Create a list of datetime objects by combining the target date with each time
    datetimes = [datetime.combine(target_date, t) for t in times]

    # Convert the list of datetime objects to strings
    result = [d.strftime('%m.%d.%Y %H:%M:%S') for d in datetimes]

    # Sort the resulting string array
    result = sorted(result, reverse=True)
    key = None
    for dt in result:
        if dt <= candle_15_min["Date"]:
            key = dt
            break
    
    if key is None:
        key = pd.to_datetime(candle_15_min["Date"]) - timedelta(days=1)
        key = datetime.combine(key, time(hour=21, minute=0, second=0))

    # Convert key to a Timestamp object
    key_timestamp = pd.to_datetime(key, format='%m.%d.%Y %H:%M:%S')
    # Use the key_timestamp to access the value in kijun_h4

    #formatted_timestamp = key_timestamp.strftime('%m.%d.%Y %H:%M:%S')
    if key_timestamp not in kijun_h4:
        key_timestamp = min(kijun_h4.keys(), key=lambda x: abs((x - key_timestamp).total_seconds()))
    
    return kijun_h4[key_timestamp]

def fibonacci_78_6(x, y):
    retracement_level = 0.786
    return y + (x - y) * retracement_level

def calculate_risk_reward_ratio(entry_price, target_price, stop_loss_price):
    print('calculating risk reward ratio...')
    print('entry_price: '+str(entry_price))
    print('target_price: '+str(target_price))
    print('stop_loss_price: '+str(stop_loss_price))
    risk = abs(entry_price - stop_loss_price)
    print('risk: '+str(risk))
    reward = abs(target_price - entry_price)
    print('reward: '+str(reward))
    if risk == 0:
        return 0  # if risk is 0, the risk/reward ratio is theoretically infinite
    risk_reward_ratio = reward / risk
    print('risk_reward_ratio: '+str(risk_reward_ratio))
    return risk_reward_ratio

def calculate_target_price_LONG(entry_price, stop_loss_price, risk_reward_ratio):
    """
    Calculate target price given entry price, stop loss price, and risk/reward ratio.

    Parameters:
    entry_price (float): Entry price of the trade.
    stop_loss_price (float): Stop loss price of the trade.
    risk_reward_ratio (float): Risk/reward ratio.

    Returns:
    float: Target price.
    """
    risk = abs(entry_price - stop_loss_price)
    reward = risk * risk_reward_ratio
    target_price = entry_price + reward
    return target_price

def calculate_target_price_SHORT(entry_price, stop_loss_price, risk_reward_ratio):
    """
    Calculate target price given entry price, stop loss price, and risk/reward ratio.

    Parameters:
    entry_price (float): Entry price of the trade.
    stop_loss_price (float): Stop loss price of the trade.
    risk_reward_ratio (float): Risk/reward ratio.

    Returns:
    float: Target price.
    """
    risk = abs(entry_price - stop_loss_price)
    reward = risk * risk_reward_ratio
    target_price = entry_price - reward
    return target_price

def calculate_stop_loss_LONG(pair, entry_price, lowest_price):
    print('calculate_stop_loss_LONG: entry_price '+ str(entry_price)+' - lowest_price: '+ str(lowest_price))
    
    if 'JPY' in pair:
        pips_difference = (entry_price - lowest_price) * 100 # convert to pips
    else:
        pips_difference = (entry_price - lowest_price) * 10000 # convert to pips

    print('pips_difference: '+str(pips_difference))
    pips_difference = round(pips_difference)
    print('pips_difference_rounded: '+str(pips_difference))

    # Apply the rules for modifying pips_difference
    if pips_difference <= 8:
        pips_difference = 15
    elif 9 <= pips_difference <= 11:
        pips_difference = 20
    elif 12 <= pips_difference <= 18:
        pips_difference += 10
    elif 19 <= pips_difference <= 20:
        pips_difference = 30
    elif 21 <= pips_difference <= 24:
        pips_difference = 35
    elif 25 <= pips_difference <= 29:
        pips_difference = 40
    elif pips_difference == 30:
        pips_difference = 45
    elif 31 <= pips_difference <= 39:
        pips_difference = 50
    elif pips_difference == 40:
        pips_difference = 55
    elif 41 <= pips_difference <= 49:
        pips_difference = 60
    elif 50 <= pips_difference <= 59:
        pips_difference = 70
    elif 60 <= pips_difference <= 69:
        pips_difference = 80
    elif 70 <= pips_difference <= 79:
        pips_difference = 90
    elif pips_difference >= 80:
        pips_difference = (math.ceil(pips_difference / 10) * 10) + 10

    print('pips: '+str(pips_difference))
    if 'JPY' in pair:
        stop_loss_price = entry_price - pips_difference / 100  # convert back to price
    else:
        stop_loss_price = entry_price - pips_difference / 10000  # convert back to price

    print('stop_loss_price: '+str(stop_loss_price))
    return stop_loss_price

def calculate_stop_loss_SHORT(pair, entry_price, highest_price):
    print('calculate_stop_loss_SHORT: entry_price '+ str(entry_price)+' - highest_price: '+ str(highest_price))
    
    if 'JPY' in pair:
        pips_difference = (highest_price - entry_price) * 100  # convert to pips
    else:
        pips_difference = (highest_price - entry_price) * 10000  # convert to pips

    print('pips_difference: '+str(pips_difference))
    pips_difference = round(pips_difference)
    print('pips_difference_rounded: '+str(pips_difference))

    # Apply the rules for modifying pips_difference
    if pips_difference <= 8:
        pips_difference = 15
    elif 9 <= pips_difference <= 11:
        pips_difference = 20
    elif 12 <= pips_difference <= 18:
        pips_difference += 10
    elif 19 <= pips_difference <= 20:
        pips_difference = 30
    elif 21 <= pips_difference <= 24:
        pips_difference = 35
    elif 25 <= pips_difference <= 29:
        pips_difference = 40
    elif pips_difference == 30:
        pips_difference = 45
    elif 31 <= pips_difference <= 39:
        pips_difference = 50
    elif pips_difference == 40:
        pips_difference = 55
    elif 41 <= pips_difference <= 49:
        pips_difference = 60
    elif 50 <= pips_difference <= 59:
        pips_difference = 70
    elif 60 <= pips_difference <= 69:
        pips_difference = 80
    elif 70 <= pips_difference <= 79:
        pips_difference = 90
    elif pips_difference >= 80:
        pips_difference = (math.ceil(pips_difference / 10) * 10) + 10

    print('pips: '+str(pips_difference))

    if 'JPY' in pair:
        stop_loss_price = entry_price + (pips_difference / 100)  # convert back to price
    else:
        stop_loss_price = entry_price + (pips_difference / 10000)  # convert back to price

    print('stop_loss_price: '+str(stop_loss_price))
    return stop_loss_price

def process_trades_LONG(history_DLY, zone_rectY1_DLY, history_15, pair, start_index, kijun_h4, stop_loss, initial_sl, entry_price, tp, zone_rectY1_H4, history_H4, entry_date):
    enddate = None
    Continue = False
    Partial = False
    H4_broken = False
    DLY_broken = False
    target_price = tp
    target_1_1 = calculate_target_price_LONG(entry_price, stop_loss, 1)
    
    #print('candles to  '+str(len(history_15) - start_index))
    print('entry_price: '+str(entry_price))
    print('stop_loss: '+str(stop_loss))
    print('target 1:1: '+str(target_1_1))
    
    for index in range(start_index, len(history_15)):
        enddate = history_15[index]['Date']
        if not DLY_broken and not H4_broken:
            target_price = get_nearest_lower_kijun_h4(history_15[index], kijun_h4)
            risk_reward = calculate_risk_reward_ratio(entry_price, target_price, initial_sl)
            partial_target = get_rr_range(risk_reward)

        if history_15[index]['BidHigh'] >= target_price:
            print('history_15 < target price: '+str(history_15[index]['BidHigh']))
            # Send operation to Salesforce
            #salesforce.send_operation(pair, 'close')

            # Set 'close' to the status pair on trades table
            update_trade_closed(pair, 'TARGET', 'FULL', history_15[index]['Date'], risk_reward)
            Continue = True
            break

        elif history_15[index]['BidLow'] <= stop_loss:
            print('history_15 < stop_loss: '+str(history_15[index]['BidLow']))
            # Send operation to Salesforce
            #salesforce.send_operation(pair, 'stop loss')
            
            # Set 'close' to pair on trades table
            pt = get_partial_trade_closed(pair, entry_date)
            if pt:
                if pt['stop_loss'] != stop_loss:
                    rr = calculate_risk_reward_ratio(pt['entry_price'], stop_loss, pt['stop_loss'])
                    update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], rr)
                else:
                    update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], -1)
            else:
                update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], -1)

            Continue = True
            break
        
        elif history_15[index]['BidHigh'] >= target_1_1:
            partial_trade = get_partial_trade(pair)
            if partial_trade:
                # Update stoploss to entry price
                
                update_trade_stoploss(pair, entry_price, index, 0)
                stop_loss = entry_price
                # Set 'close' to pair from trades table
                update_trade_closed(pair, 'TARGET', 'PARTIAL', history_15[index]['Date'], 1)
                close_mt5_partial_positions(pair)
                # Send operation to Salesforce
                #salesforce.send_operation(pair, 'partial close')
        print('partial_target: '+str(partial_target))
        while partial_target:
            partial_target_price = calculate_target_price_LONG(entry_price, initial_sl, partial_target[0])
            print('partial_target_price: '+str(partial_target_price))
            print('partial_target[0]-2: '+str(partial_target[0]-2))
            if history_15[index]['BidHigh'] >= partial_target_price:
                sl = calculate_target_price_LONG(entry_price, initial_sl, partial_target[0]-2)
                update_trade_stoploss(pair, sl, index, partial_target[0]-2) 
                partial_target.pop(0)
                stop_loss = sl
            else:
                break
        
        if not DLY_broken and not H4_broken:
            update_trade_target(pair, target_price, risk_reward)  
        
        # check if DLY was broken
        if history_DLY[-1]["Date"] == history_15[index]["Date"] and history_DLY[-1]["BidClose"] < zone_rectY1_DLY:
            print(" DLY close: ",history_DLY[-1]["BidClose"])
            print(" zone_rectY1_DLY: ",zone_rectY1_DLY)
            print ('******* DLY_broken: '+str(history_15[index]["Date"]))
            DLY_broken = True
            risk_reward = 0
            
            if history_DLY[-1]["BidClose"] < entry_price:
                target_price = entry_price
                target_1_1 = entry_price
                partial_target = []
            else:
                stop_loss = entry_price

            update_trade_target_ALL(pair, entry_price, risk_reward)

        # check if H4 was broken
        dt = pd.to_datetime(history_15[index]["Date"], format='%m.%d.%Y %H:%M:%S')
        if dt in kijun_h4.keys():
            h4BidClose = get_H4BidClose(history_15[index]["Date"], history_H4)
            print ('******* h4BidClose: '+str(h4BidClose)+' - zone_rectY1_H4: '+str(zone_rectY1_H4))
            if h4BidClose is not None and h4BidClose < zone_rectY1_H4:
                #update target with entry price
                print ('******* H4_broken: '+str(history_15[index]["Date"]))
                #print ('******* target: '+str(entry_price))
                H4_broken = True
                risk_reward = 0

                if h4BidClose < entry_price:
                    target_price = entry_price
                    target_1_1 = entry_price
                    partial_target = []
                else:
                    stop_loss = entry_price

                update_trade_target_ALL(pair, entry_price, risk_reward) 

    
    return Continue, enddate

def process_trades_SHORT(history_DLY, zone_rectY1_DLY, history_15, pair, start_index, kijun_h4, stop_loss, initial_sl, entry_price, tp, zone_rectY1_H4, history_H4, entry_date):
    enddate = None
    Continue = False
    Partial = False
    H4_broken = False
    DLY_broken = False
    target_price = tp
    target_1_1 = calculate_target_price_SHORT(entry_price, stop_loss, 1)
    print('start_index: '+str(start_index))
    print('len(history_15): '+str(len(history_15)))
    # print('start_index_date: '+str(history_15[start_index]['Date']))
    print('target_1_1: '+str(target_1_1))
    print('initial_sl: '+str(initial_sl))
    
    for index in range(start_index, len(history_15)):
        enddate = history_15[index]['Date']
        if not DLY_broken and not H4_broken:
            target_price = get_nearest_lower_kijun_h4(history_15[index], kijun_h4)
            risk_reward = calculate_risk_reward_ratio(entry_price, target_price, initial_sl)
            partial_target = get_rr_range(risk_reward)
        
        if history_15[index]['BidLow'] <= target_price:
            print('history_15 < target price: '+str(history_15[index]['BidLow']))
            # Send operation to Salesforce
            #salesforce.send_operation(pair, 'close')

            # Set 'close' to the status pair on trades table
            update_trade_closed(pair, 'TARGET', 'FULL', history_15[index]['Date'], risk_reward)
            Continue = True
            break

        elif history_15[index]['BidHigh'] >= stop_loss:
            print('history_15 > stop_loss: '+str(history_15[index]['BidHigh']))
            # Send operation to Salesforce
            #salesforce.send_operation(pair, 'stop loss')
            
            # Set 'close' to pair on trades table
            pt = get_partial_trade_closed(pair, entry_date)
            if pt:
                if pt['stop_loss'] != stop_loss:
                    rr = calculate_risk_reward_ratio(pt['entry_price'], stop_loss, pt['stop_loss'])
                    update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], rr)
                else:
                    update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], -1)
            else:
                update_trade_closed(pair, 'STOP LOSS', 'FULL', history_15[index]['Date'], -1)

            Continue = True
            break
        
        elif history_15[index]['BidLow'] <= target_1_1:
            print('history_15 < target_1_1: '+str(history_15[index]['BidLow']))
            partial_trade = get_partial_trade(pair)
            if partial_trade:
                # Update stoploss to entry price
                #print('entry_price: '+str(entry_price))
                #print('index: '+str(index))
                update_trade_stoploss(pair, entry_price, index, 0)
                stop_loss = entry_price
                # Set 'close' to pair from trades table
                update_trade_closed(pair, 'TARGET', 'PARTIAL', history_15[index]['Date'], 1)
                close_mt5_partial_positions(pair)

        while partial_target:
            partial_target_price = calculate_target_price_SHORT(entry_price, initial_sl, partial_target[0])
            #print('partial_target_price: '+str(partial_target_price))
            #print('partial_target[0]-2: '+str(partial_target[0]-2))
            if history_15[index]['BidLow'] <= partial_target_price:
                sl = calculate_target_price_SHORT(entry_price, initial_sl, partial_target[0]-2)
                #print(f'new_stop_loss from partial {partial_target[0]}: '+str(sl))
                update_trade_stoploss(pair, sl, index, partial_target[0]-2)
                partial_target.pop(0)
                stop_loss = sl
            else:
                break  
        
        if not DLY_broken and not H4_broken:
            update_trade_target(pair, target_price, risk_reward)   

        # check if DLY was broken
        if history_DLY[-1]["Date"] == history_15[index]["Date"] and history_DLY[-1]["BidClose"] > zone_rectY1_DLY:
            print(" DLY close: ",history_DLY[-1]["BidClose"])
            print(" zone_rectY1_DLY: ",zone_rectY1_DLY)
            print ('******* DLY_broken: '+str(history_15[index]["Date"]))
            DLY_broken = True
            risk_reward = 0

            if history_DLY[-1]["BidClose"] > entry_price:
                target_price = entry_price
                target_1_1 = entry_price
                partial_target = []
            else:
                stop_loss = entry_price
            
            update_trade_target_ALL(pair, entry_price, risk_reward) 

        # check if H4 was broken
        dt = pd.to_datetime(history_15[index]["Date"], format='%m.%d.%Y %H:%M:%S')
        if dt in kijun_h4.keys():
            h4BidClose = get_H4BidClose(history_15[index]["Date"], history_H4)
            print ('******* h4BidClose: '+str(h4BidClose)+' - zone_rectY1_H4: '+str(zone_rectY1_H4))
            if h4BidClose is not None and h4BidClose > zone_rectY1_H4:
                #update target with entry price
                print ('******* H4_broken: '+str(history_15[index]["Date"]))
                print ('******* target: '+str(entry_price))
                H4_broken = True
                risk_reward = 0

                if h4BidClose > entry_price:
                    target_price = entry_price
                    target_1_1 = entry_price
                    partial_target = []
                else:
                    stop_loss = entry_price

                update_trade_target_ALL(pair, entry_price, risk_reward) 

    return Continue, enddate

def get_rr_range(risk_reward):
    if risk_reward == float('inf') or risk_reward == 0:
        return []
    rr_ceil = math.ceil(risk_reward)
    if rr_ceil > 3:
        return list(range(3, rr_ceil))
    else:
        return []

def count_entries_on_date(data, date):
    
    count = 0
    for entry in data:
        datetime_object = datetime.strptime(entry['Date'], "%m.%d.%Y %H:%M:%S")
        date_object = datetime_object.date()
        if date_object == date:
            count += 1
    return count


def verify_trade_in_retest(trade, history_m15):
    start_session = 0
    broken = False
    retest_date = None
    for index in range(start_session, len(history_m15)):
        if history_m15[index]['Date'] < trade['pattern_x1']:
            continue

        if trade['direction'] == 'LONG':
            if broken == False and history_m15[index]['BidClose'] > trade['pattern_y1']:
                broken = True
            if broken == True and history_m15[index]['BidLow'] <= trade['entry_price']:
                retest_date = history_m15[index]['Date']
                break


        if trade['direction'] == 'SHORT':
            if broken == False and history_m15[index]['BidClose'] < trade['pattern_y1']:
                broken = True
            if broken == True and history_m15[index]['BidHigh'] >= trade['entry_price']:
                retest_date = history_m15[index]['Date']
                break
    
    return retest_date


def process_trade_in_retest(trade, history_m15, kijun_h4, history_H4):
    continue_logic = False
    start_session = 0
    broken = False
    trade_setup = []
    pattern_date = datetime.strptime(trade['breakup_date'], '%m.%d.%Y %H:%M:%S')
    
    if trade['direction'] == 'LONG':
        if history_H4[-2]['BidClose'] < trade['zones_rectY1_H4']:
            close_trade_in_retest(trade['pair'])
            continue_logic = True
            return continue_logic
    elif trade['direction'] == 'SHORT':
        if history_H4[-2]['BidClose'] > trade['zones_rectY1_H4']:
            close_trade_in_retest(trade['pair'])
            continue_logic = True
            return continue_logic

            
    for index in range(start_session, len(history_m15)):
        index_date = datetime.strptime(history_m15[index]['Date'], '%m.%d.%Y %H:%M:%S')
        if index_date < pattern_date:
            continue
       
        if trade['direction'] == 'LONG':

            if index_date == pattern_date:
                broken = True
                higher_high = history_m15[index]['BidHigh']
                lowest_low = (0.786 * higher_high - higher_high + trade['entry_price'])/ 0.786
                continue

            if broken == False and history_m15[index]['BidClose'] > trade['pattern_y1']:
                broken = True
                higher_high = history_m15[index]['BidHigh']
                lowest_low = (0.786 * higher_high - higher_high + trade['entry_price'])/ 0.786 
                
                print('broken date: '+str(history_m15[index]['Date'] ))
            elif broken == True:
                if history_m15[index]['BidLow'] <= trade['entry_price']:
                    print('retest date: '+str(history_m15[index]['Date'] ))
                    update_trade_in_progress(trade['pair'], index, history_m15[index]['Date'])
                    continue_logic = True
                    break
                elif history_m15[index]['BidHigh'] >= get_nearest_lower_kijun_h4(history_m15[index], kijun_h4):
                    print('BidHigh >= get_nearest_lower_kijun_h4')
                    close_trade_in_retest(trade['pair'])
                    continue_logic = True
                    break
                elif history_m15[index]['BidHigh'] > higher_high:
                    higher_high = history_m15[index]['BidHigh']
                    
                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                    fib_78_6 = fibonacci_78_6(lowest_low, higher_high)
                    print('fib_78_6: '+str(fib_78_6)+' - pattern_Y1: '+str(trade['pattern_Y1']))
                    if fib_78_6 > trade['pattern_Y1']:
                        print('fib_78_6 has surpassed the pattern') 
                        close_trade_in_retest(trade['pair'])
                        continue_logic = True
                        break
                    risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, trade['stop_loss'])
                    if  risk_reward >= 2:
                        trade_setup.append({'pair': trade['pair'], 
                                            'entry_price': fib_78_6, 
                                            'stop_loss_price':trade['stop_loss'], 
                                            'target_price': target_price, 
                                            'direction': 'LONG', 
                                            'risk_reward': risk_reward,
                                            'type': trade['trade_type'], 
                                            'zones_rectX1_DLY': str(trade['zones_rectX1_DLY']),
                                            'zones_rectY1_DLY': trade['zones_rectY1_DLY'],
                                            'zones_rectY2_DLY': trade['zones_rectY2_DLY'],
                                            'zones_rectX1_H4': str(trade['zones_rectX1_H4']),
                                            'zones_rectY1_H4': trade['zones_rectY1_H4'], 
                                            'zones_rectY2_H4': trade['zones_rectY2_H4'],
                                            'pattern_x1': str(trade['pattern_x1']),
                                            'pattern_y1': trade['pattern_Y1'],
                                            'pattern_y2': trade['pattern_y2'],
                                            'breakup_date': history_m15[index]['Date']})
                        
                        target_1_1 = calculate_target_price_LONG(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                        print('trade direction long: '+str(trade['direction']))
                        upsert_order_waiting_retest(trade_setup[-1], target_1_1)
                    else: 
                        print('NO RR') 
                        close_trade_in_retest(trade['pair'])
                        continue_logic = True
                        break
                else:
                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                    if target_price != trade['target']:
                        risk_reward = calculate_risk_reward_ratio(trade['entry_price'], target_price, trade['stop_loss'])
                        if risk_reward >= 2:
                            update_trade_target(trade['pair'], target_price, risk_reward)
                        else:
                            print('NO RR: '+str(risk_reward)) 
                            close_trade_in_retest(trade['pair'])
                            continue_logic = True
                            break




        elif trade['direction'] == 'SHORT':

            if index_date == pattern_date:
                broken = True 
                lowest_low = history_m15[index]['BidLow']
                higher_high = (0.786 * lowest_low - lowest_low + trade['entry_price'])/ 0.786 
                continue

            if broken == False and history_m15[index]['BidClose'] < trade['pattern_y1']:
                broken = True

                lowest_low = history_m15[index]['BidLow']
                higher_high = (0.786 * lowest_low - lowest_low + trade['entry_price'])/ 0.786 
                print('broken date: '+str(history_m15[index]['Date'] ))
            elif broken == True:
                if history_m15[index]['BidHigh'] >= trade['entry_price']:
                    print('retest date: '+str(history_m15[index]['Date'] ))
                    update_trade_in_progress(trade['pair'], index, history_m15[index]['Date'])
                    continue_logic = True
                    break
                elif history_m15[index]['BidLow'] <= get_nearest_lower_kijun_h4(history_m15[index], kijun_h4):
                    print('BidLow <= get_nearest_lower_kijun_h4') 
                    close_trade_in_retest(trade['pair'])
                    continue_logic = True
                    break
                elif history_m15[index]['BidLow'] < lowest_low:
                    lowest_low = history_m15[index]['BidLow']
                    
                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                    fib_78_6 = fibonacci_78_6(higher_high, lowest_low)
                    print('fib_78_6: '+str(fib_78_6)+' - pattern_Y1: '+str(trade['pattern_Y1']))
                    if fib_78_6 < trade['pattern_Y1']:
                        print('fib_78_6 has surpassed the pattern') 
                        close_trade_in_retest(trade['pair'])
                        continue_logic = True
                        break

                    risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, trade['stop_loss'])
                    if  risk_reward >= 2:
                        trade_setup.append({'pair': trade['pair'], 
                                            'entry_price': fib_78_6, 
                                            'stop_loss_price':trade['stop_loss'], 
                                            'target_price': target_price, 
                                            'direction': 'SHORT', 
                                            'risk_reward': risk_reward,
                                            'type': trade['trade_type'],  
                                            'zones_rectX1_DLY': str(trade['zones_rectX1_DLY']),
                                            'zones_rectY1_DLY': trade['zones_rectY1_DLY'],
                                            'zones_rectY2_DLY': trade['zones_rectY2_DLY'],
                                            'zones_rectX1_H4': str(trade['zones_rectX1_H4']),
                                            'zones_rectY1_H4': trade['zones_rectY1_H4'], 
                                            'zones_rectY2_H4': trade['zones_rectY2_H4'],
                                            'pattern_x1': str(trade['pattern_x1']),
                                            'pattern_y1': trade['pattern_Y1'],
                                            'pattern_y2': trade['pattern_y2'],
                                            'breakup_date': history_m15[index]['Date']})
                        
                        target_1_1 = calculate_target_price_SHORT(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                        print('trade direction short: '+str(trade['direction']))
                        upsert_order_waiting_retest(trade_setup[-1], target_1_1)
                    else:  
                        print('NO RR') 
                        close_trade_in_retest(trade['pair'])
                        continue_logic = True
                        break
                else:
                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                    if target_price != trade['target']:
                        risk_reward = calculate_risk_reward_ratio(trade['entry_price'], target_price, trade['stop_loss'])
                        if risk_reward >= 2:
                            update_trade_target(trade['pair'], target_price, risk_reward)
                        else:
                            print('NO RR: '+str(risk_reward))
                            close_trade_in_retest(trade['pair'])
                            continue_logic = True
                            break
    print('trade in retest processed')
    return continue_logic
                    
def clean_trades(): 
    close_mt5_orders_already_processed()

def get_H4BidClose(date, history_H4):
    for i in range(1, len(history_H4)):
        if history_H4[i]['Date'] == date:
            return history_H4[i-1]['BidClose'] 
    return None


     



    
    
                
            
