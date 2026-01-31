import argparse
import pandas as pd
import common_samples
import os

from forexconnect import ForexConnect, fxcorepy
from datetime import datetime, timedelta, time
from db_utils import check_in_retest_trade, check_in_progress_trade, get_stop_loss, check_in_closed_trade, remove_closed_trades, update_trade_in_progress, upsert_order_waiting_retest, close_trade_in_retest, get_closed_trades_after_date, initialize_signals_db, SIMULATION_MODE
from utils import *

def parse_args():
    parser = argparse.ArgumentParser(description='Process command parameters.') 
    common_samples.add_main_arguments(parser)
    common_samples.add_instrument_timeframe_arguments(parser)
    common_samples.add_date_arguments(parser)
    common_samples.add_max_bars_arguments(parser)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    str_user_id = args.l
    str_password = args.p
    str_url = args.u
    str_connection = args.c
    str_session_id = args.session
    str_pin = args.pin
    str_instrument = args.i
    #str_timeframe = args.timeframe
    quotes_count = args.quotescount
    date_from = args.datefrom
    date_to = args.dateto
    str_session = args.session
    watchlist = []
    
    # Inizializza il database dei segnali MT5 (per modalità simulazione)
    if SIMULATION_MODE:
        print("=" * 60)
        print("  RUNNING IN SIMULATION MODE (No MT5)")
        print("  Signals will be logged to SQLite database")
        print("=" * 60)
        initialize_signals_db()

    with ForexConnect() as fx:
        try:
            # Usa il path dello script corrente invece di un path hardcodato
            script_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(script_dir)

            fx.login(str_user_id, str_password, str_url,
                     str_connection, str_session_id, str_pin,
                     common_samples.session_status_changed)
            #fx.login(str_user_id, str_password, str_url,
                     #str_connection, str_session_id, str_pin,
                     #None)

            print("")
            print("Requesting a price history...")

            history_DLY = fx.get_history(str_instrument, 'D1', date_from, date_to, quotes_count)
            history_DLY = format_history(history_DLY,'DLY')
            history_H4 = fx.get_history(str_instrument, 'H4', date_from, date_to, quotes_count)
            history_H4 = format_history(history_H4,'H4')
            history_m15 = fx.get_history(str_instrument, 'm15', date_from, date_to, quotes_count)
            history_m15 = format_history(history_m15,'m15')
            
            print("history retrieved.")

            if str_session == 'Trade' or str_session == 'BT' or str_session == 'BTLOG':
                kijun_period = 26
                
                lastclosearray = []
                zones_rectX1 = []
                zones_rectX2 = []
                zones_rectY1 = []
                zones_rectY2 = []
                final_zones =  []
                zone = 0
                enddate = None
                DLY_valid_zone = False
                trade_keys = ['pair', 'status', 'trade_type', 'entry_date', 'close_date', 'entry_price', 'entry_price_index', 'stop_loss', 'target', 'direction', 'initial_risk_reward', 'final_risk_reward', 'profit', 'result', 'zones_rectx1_dly', 'zones_recty1_dly', 'zones_recty2_dly', 'zones_rectx1_h4', 'zones_recty1_h4', 'zones_recty2_h4', 'patter_x1', 'patter_y1', 'patter_y2']

                
                kijun_h4 = calculate_kijun(history_H4, kijun_period)
                continue_logic = True
                start_session = len(history_DLY)-1 
                
                trade_in_retest = check_in_retest_trade(str_instrument)

                print('Trade in retest: '+str(trade_in_retest))
                
                if trade_in_retest is not None:
                    continue_logic = process_trade_in_retest(trade_in_retest, history_m15, kijun_h4, history_H4)

                trade_in_progress = None
                if continue_logic:
                    trade_in_progress = check_in_progress_trade(str_instrument)
                
                print('Trade in progress: '+str(trade_in_progress))

                if trade_in_progress is not None:
                    trade_in_progress = dict(zip(trade_keys, trade_in_progress))
                    print('trade_in_progress: '+str(trade_in_progress))
                    if trade_in_progress['direction'] == 'LONG':
                        initial_stop_loss = get_stop_loss(str_instrument, trade_in_progress['entry_date'])
                        print('initial_stop_loss: '+str(initial_stop_loss))
                        continue_logic, enddate = process_trades_LONG(history_DLY, trade_in_progress['zones_recty1_dly'], history_m15, str_instrument, trade_in_progress['entry_price_index']+1, kijun_h4, trade_in_progress['stop_loss'],  initial_stop_loss, trade_in_progress['entry_price'], trade_in_progress['target'], trade_in_progress['zones_recty1_h4'], history_H4, trade_in_progress['entry_date'])
                        print('continue_logic: '+str(continue_logic))
                    
                    elif trade_in_progress['direction'] == 'SHORT':
                        initial_stop_loss = get_stop_loss(str_instrument, trade_in_progress['entry_date'])
                        print('initial_stop_loss: '+str(initial_stop_loss))
                        continue_logic, enddate = process_trades_SHORT(history_DLY, trade_in_progress['zones_recty1_dly'], history_m15, str_instrument, trade_in_progress['entry_price_index']+1, kijun_h4, trade_in_progress['stop_loss'], initial_stop_loss, trade_in_progress['entry_price'], trade_in_progress['target'], trade_in_progress['zones_recty1_h4'], history_H4, trade_in_progress['entry_date'])
                        print('continue_logic: '+str(continue_logic))
                 
                #continue_logic = False #to break the flow
                print('continue_logic: '+str(continue_logic))
                if continue_logic: 
                    for index in range(start_session, len(history_DLY)):
        
                        zones_rectX1_DLY, zones_rectX2_DLY, zones_rectY1_DLY, zones_rectY2_DLY, final_zones_DLY, zone_type_DLY = get_zones(history_DLY, kijun_h4, index, 'DLY', str_session, None)
                        print('final_zones_DLY '+str(final_zones_DLY))
                        if len(final_zones_DLY) != 0:
                            print('zone_type_DLY '+str(zone_type_DLY))
                            
                        if len(final_zones_DLY) == 0:
                            continue

                        for zone in reversed(final_zones_DLY):
                            if zone_type_DLY == 'SUP':
                                DLY_candle, DLY_zone_valid_for_kijun, DLY_valid_zone, anchor = validate_support(zones_rectX1_DLY[zone], zones_rectX2_DLY[zone], zones_rectY1_DLY[zone], zones_rectY2_DLY[zone], history_DLY, 'DLY', kijun_h4, str_instrument, 'Trade')
                            elif zone_type_DLY == 'RES':
                                DLY_candle, DLY_zone_valid_for_kijun, DLY_valid_zone, anchor = validate_resistence(zones_rectX1_DLY[zone], zones_rectX2_DLY[zone], zones_rectY1_DLY[zone], zones_rectY2_DLY[zone], history_DLY, 'DLY', kijun_h4, str_instrument, 'Trade')
                            
                            dly_zone = zone
                            print('zones_rectX1_DLY zone: '+str(zones_rectX1_DLY[dly_zone]))
                            print('zones_rectY1_DLY zone: '+str(zones_rectY1_DLY[dly_zone]))
                            print('zones_rectY2_DLY zone: '+str(zones_rectY2_DLY[dly_zone]))
                            print('DLY_valid_zone: '+str(DLY_valid_zone))
                            if DLY_valid_zone:
                                break

                        
                        if DLY_valid_zone: 
                            watchlist.append(':ballot_box_with_check: In attesa della zona H4 su: '+str_instrument)
                            #search in H4 timeframe
                            print('dly candle: '+str(DLY_candle["Date"]))
                            index_of_last_candle = get_index_of_last_h4_candle_on_daily_date(history_H4, DLY_candle["Date"], str_session, date_to)
                            print('index of last candle: '+str(index_of_last_candle))
                            #input()
                            zones_rectX1_H4, zones_rectX2_H4, zones_rectY1_H4, zones_rectY2_H4, final_zones_H4, zone_type_H4 = get_zones(history_H4, kijun_h4,len(history_H4)-1 , 'H4', str_session, zones_rectX1_DLY[dly_zone])
                            h4_zone = -1                        
                            H4_valid_zone = False
                            if zone_type_H4 == 'SUP':
                                for zone in reversed(final_zones_H4):
                                    if (zones_rectY1_H4[zone] <= zones_rectY2_DLY[dly_zone] and
                                    history_H4[-2]['BidClose'] >= zones_rectY1_H4[zone]):
                                        h4_zone = zone
                                        H4_candle, H4_zone_valid_for_kijun, H4_valid_zone, anchor_15_min = validate_support(zones_rectX1_H4[h4_zone], zones_rectX2_H4[h4_zone], zones_rectY1_H4[h4_zone], zones_rectY2_H4[h4_zone], history_H4, 'H4', kijun_h4, str_instrument, 'Trade')
                                        if H4_valid_zone:
                                            break
                                if len(zones_rectX1_H4) != 0:
                                    print('zones_rectX1_H4 zone: '+str(zones_rectX1_H4[h4_zone]))
                                    print('zones_rectY1_H4 zone: '+str(zones_rectY1_H4[h4_zone]))
                                    print('zones_rectY2_H4 zone: '+str(zones_rectY2_H4[h4_zone]))
                            
                                print('H4_valid_zone '+str(H4_valid_zone))
                                if H4_valid_zone:
                                    watchlist.append(':ballot_box_with_check: In attesa di un pattern: '+str_instrument)
                                    
                                    print('search pattern m15')
                                    pattern_rectX1, pattern_rectX2, pattern_rectY1, pattern_rectY2, lastlow = get_pattern_m15_SUP(history_m15, kijun_h4, anchor_15_min, zones_rectX2_H4[zone], zones_rectY1_H4[zone], zones_rectY2_H4[zone],str_instrument,str_session)

                                    if(pattern_rectX1 is not None):
                                        
                                        #check if the same pattern was closed 
                                        trade_closed = check_in_closed_trade(str_instrument, pattern_rectX1)
                                        if trade_closed:
                                            print('pattern already evaluated')
                                            break

                                        if enddate is not None and pattern_rectX1 < enddate:
                                            print('the pattern preceding a just-closed trade')
                                            break
                                        
                                        result = get_closed_trades_after_date(str_instrument, pattern_rectX1)
                                        if result:
                                            print('the pattern preceding a closed trade')
                                            break


                                        watchlist.append(':ballot_box_with_check: In attesa rottura pattern: '+str_instrument)

                                        print('pattern_rectX1: '+str(pattern_rectX1))
                                        print('pattern_rectX2: '+str(pattern_rectX2))
                                        print('pattern_rectY1: '+str(pattern_rectY1))
                                        print('pattern_rectY2: '+str(pattern_rectY2))

                                        #start of the analysis to open a position
                                        pattern_breaking = False
                                        pattern_breaking_candle = []
                                        pattern_breaking_candle_high = 0
                                        fib_78_6 = 0
                                        index_lastlow = 0
                                        trade_setup = []
                                        for index in range(pattern_rectX2, len(history_m15)-1):
                                            
                                            if (pattern_breaking == False and 
                                                history_m15[index]['BidClose'] > pattern_rectY1):

                                                pattern_breaking = True 
                                                pattern_breaking_candle = history_m15[index]
                                                pattern_breaking_candle_high = history_m15[index]['BidHigh']
                                                fib_78_6 = fibonacci_78_6(lastlow, pattern_breaking_candle_high)

                                                print('fib_78_6: '+str(fib_78_6))
                                                print('lastlow: '+str(lastlow))
                                                print('pattern_breaking_candle_high: '+str(pattern_breaking_candle_high))
                                                ###################
                                                stop_loss_price = calculate_stop_loss_LONG(str_instrument,pattern_rectY1, lastlow)
                                                target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                                                risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, stop_loss_price)
                                                if  risk_reward >= 2:
                                                    trade_setup.append({'pair': str_instrument, 
                                                                        'entry_price': fib_78_6, 
                                                                        'stop_loss_price':stop_loss_price, 
                                                                        'target_price': target_price, 
                                                                        'direction': 'LONG', 
                                                                        'type':'FULL',
                                                                        'risk_reward': risk_reward, 
                                                                        'zones_rectX1_DLY': str(zones_rectX1_DLY[dly_zone]),
                                                                        'zones_rectY1_DLY': zones_rectY1_DLY[dly_zone],
                                                                        'zones_rectY2_DLY': zones_rectY2_DLY[dly_zone],
                                                                        'zones_rectX1_H4': str(zones_rectX1_H4[h4_zone]),
                                                                        'zones_rectY1_H4': zones_rectY1_H4[h4_zone], 
                                                                        'zones_rectY2_H4': zones_rectY2_H4[h4_zone],
                                                                        'pattern_x1': str(pattern_rectX1),
                                                                        'pattern_y1': pattern_rectY1,
                                                                        'pattern_y2': pattern_rectY2,
                                                                        'breakup_date':history_m15[index]['Date'],
                                                                        'fibonacci100':lastlow})
                                                    
                                                    target_1_1 = calculate_target_price_LONG(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                                                    upsert_order_waiting_retest(trade_setup[-1], target_1_1)
                                                else:
                                                    print('NO R:R')
                                                    watchlist.append(':ballot_box_with_check: pattern senza R:R valido: '+str_instrument)
                                                    mt5_close_order(str_instrument) #if there was a previous order placed in retest.
                                                    close_trade_in_retest(str_instrument)
                                                    break
                                                
                                                ###################
                                                watchlist.append(':ballot_box_with_check: In attesa di retest pattern: '+str_instrument)
                                            
                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidLow'] <= fib_78_6):

                                                watchlist.append(':ballot_box_with_check: A mercato: '+str_instrument)

                                                print('data della rottura del livello di fibonacci: '+str(history_m15[index]['Date']))
                                                print('signal: '+str(trade_setup[-1]))
                                                update_trade_in_progress(trade_setup[-1]['pair'], index, history_m15[index]['Date'])
                                                break

                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidHigh'] >= get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)):
                                                print('trade chiuso per aver raggiunto il target senza retest')
                                                watchlist.append(':ballot_box_with_check: trade chiuso per aver raggiunto il target senza retest: '+str_instrument)
                                                close_trade_in_retest(str_instrument)
                                                break

                                            
                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidHigh'] > pattern_breaking_candle_high):
                                                    pattern_breaking_candle_high = history_m15[index]['BidHigh']
                                                    fib_78_6 = fibonacci_78_6(lastlow, pattern_breaking_candle_high)
                                                    
                                                    ###################
                                                    stop_loss_price = calculate_stop_loss_LONG(str_instrument,pattern_rectY1, lastlow)
                                                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                                                    risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, stop_loss_price)
                                                    if risk_reward >= 2:
                                                        trade_setup.append({'pair': str_instrument, 
                                                                        'entry_price': fib_78_6, 
                                                                        'stop_loss_price':stop_loss_price, 
                                                                        'target_price': target_price, 
                                                                        'direction': 'LONG', 
                                                                        'type':'FULL',
                                                                        'risk_reward': risk_reward, 
                                                                        'zones_rectX1_DLY': str(zones_rectX1_DLY[dly_zone]),
                                                                        'zones_rectY1_DLY': zones_rectY1_DLY[dly_zone],
                                                                        'zones_rectY2_DLY': zones_rectY2_DLY[dly_zone],
                                                                        'zones_rectX1_H4': str(zones_rectX1_H4[h4_zone]),
                                                                        'zones_rectY1_H4': zones_rectY1_H4[h4_zone], 
                                                                        'zones_rectY2_H4': zones_rectY2_H4[h4_zone],
                                                                        'pattern_x1': str(pattern_rectX1),
                                                                        'pattern_y1': pattern_rectY1,
                                                                        'pattern_y2': pattern_rectY2,
                                                                        'breakup_date':history_m15[index]['Date'],
                                                                        'fibonacci100':lastlow})

                                                        target_1_1 = calculate_target_price_LONG(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                                                        upsert_order_waiting_retest(trade_setup[-1], target_1_1)
                                                    else:
                                                        print('NO R:R')
                                                        watchlist.append(':ballot_box_with_check: pattern senza R:R valido: '+str_instrument)
                                                        mt5_close_order(str_instrument) #if there was a previous order placed in retest.
                                                        close_trade_in_retest(str_instrument)
                                                        break
                                                    ###################
                                        
                            elif zone_type_H4 == 'RES':
                                #print('final_zones_H4: '+str(final_zones_H4))
                                for zone in reversed(final_zones_H4):
                                    if (zones_rectY1_H4[zone] >= zones_rectY2_DLY[dly_zone] and
                                    history_H4[-2]['BidClose'] <= zones_rectY1_H4[zone]):
                                        h4_zone = zone
                                        H4_candle, H4_zone_valid_for_kijun, H4_valid_zone, anchor_15_min = validate_resistence (zones_rectX1_H4[h4_zone], zones_rectX2_H4[h4_zone], zones_rectY1_H4[h4_zone], zones_rectY2_H4[h4_zone], history_H4, 'H4', kijun_h4, str_instrument, str_session)
                                        if H4_valid_zone:
                                            break

                                #print('h4_zone: '+str(h4_zone))
                                if len(zones_rectX1_H4) != 0:
                                    print('zones_rectX1_H4 zone: '+str(zones_rectX1_H4[h4_zone]))
                                    print('zones_rectY1_H4 zone: '+str(zones_rectY1_H4[h4_zone]))
                                    print('zones_rectY2_H4 zone: '+str(zones_rectY2_H4[h4_zone]))
                                
                                if H4_valid_zone:
                                    watchlist.append(':ballot_box_with_check: In attesa di un pattern: '+str_instrument)

                                    print('search pattern m15')
                                    pattern_rectX1, pattern_rectX2, pattern_rectY1, pattern_rectY2, lasthigh = get_pattern_m15_RES(history_m15, kijun_h4, anchor_15_min, zones_rectX2_H4[h4_zone], zones_rectY1_H4[h4_zone], zones_rectY2_H4[h4_zone],str_instrument,str_session)
                                    
                                    if(pattern_rectX1 is not None):

                                        #check if the same pattern was closed 
                                        trade_closed = check_in_closed_trade(str_instrument, pattern_rectX1)
                                        if trade_closed:
                                            print('pattern already evaluated')
                                            break

                                        if enddate is not None and pattern_rectX1 < enddate:
                                            print('the pattern preceding a just-closed trade')
                                            break

                                        result = get_closed_trades_after_date(str_instrument, pattern_rectX1)
                                        if result:
                                            print('the pattern preceding a closed trade')
                                            break
                                           
                                        watchlist.append(':ballot_box_with_check: In attesa rottura pattern: '+str_instrument)

                                        print('pattern_rectX1: '+str(pattern_rectX1))
                                        print('pattern_rectX2: '+str(pattern_rectX2))
                                        print('pattern_rectY1: '+str(pattern_rectY1))
                                        print('pattern_rectY2: '+str(pattern_rectY2))

                                        #start of the analysis to open a position
                                        pattern_breaking = False
                                        pattern_breaking_candle = []
                                        pattern_breaking_candle_low = 0
                                        fib_78_6 = 0
                                        index_lastlow = 0
                                        trade_setup = []
                                        for index in range(pattern_rectX2, len(history_m15)-1):
                                            
                                            if (pattern_breaking == False and 
                                                history_m15[index]['BidClose'] < pattern_rectY1):

                                                pattern_breaking = True 
                                                pattern_breaking_candle = history_m15[index]
                                                pattern_breaking_candle_low = history_m15[index]['BidLow']
                                                fib_78_6 = fibonacci_78_6(lasthigh, history_m15[index]['BidLow'])
                                                

                                                print('fib_78_6: '+str(fib_78_6))
                                                print('lasthigh: '+str(lasthigh))
                                                print('pattern_breaking_candle_low: '+str(pattern_breaking_candle_low))
                                            
                                                ###################
                                                stop_loss_price = calculate_stop_loss_SHORT(str_instrument,pattern_rectY1,lasthigh)
                                                target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                                                risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, stop_loss_price)
                                                
                                                if  risk_reward >= 2:
                                                    trade_setup.append({'pair': str_instrument, 
                                                                        'entry_price': fib_78_6, 
                                                                        'stop_loss_price':stop_loss_price, 
                                                                        'target_price': target_price, 
                                                                        'direction': 'SHORT', 
                                                                        'type':'FULL',
                                                                        'risk_reward': risk_reward, 
                                                                        'zones_rectX1_DLY': str(zones_rectX1_DLY[dly_zone]),
                                                                        'zones_rectY1_DLY': zones_rectY1_DLY[dly_zone],
                                                                        'zones_rectY2_DLY': zones_rectY2_DLY[dly_zone],
                                                                        'zones_rectX1_H4': str(zones_rectX1_H4[h4_zone]),
                                                                        'zones_rectY1_H4': zones_rectY1_H4[h4_zone], 
                                                                        'zones_rectY2_H4': zones_rectY2_H4[h4_zone],
                                                                        'pattern_x1': str(pattern_rectX1),
                                                                        'pattern_y1': pattern_rectY1,
                                                                        'pattern_y2': pattern_rectY2,
                                                                        'breakup_date':history_m15[index]['Date'],
                                                                        'fibonacci100':lasthigh})
                                                    
                                                    target_1_1 = calculate_target_price_SHORT(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                                                    upsert_order_waiting_retest(trade_setup[-1], target_1_1)
                                                else:
                                                    print('NO R:R')
                                                    watchlist.append(':ballot_box_with_check: pattern senza R:R valido: '+str_instrument)
                                                    mt5_close_order(str_instrument) #if there was a previous order placed in retest.
                                                    close_trade_in_retest(str_instrument)
                                                    break

                                                watchlist.append(':ballot_box_with_check: In attesa di retest pattern: '+str_instrument)

                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidHigh'] >= fib_78_6):
                                                                                                
                                                watchlist.append(':ballot_box_with_check: A mercato: '+str_instrument)

                                                print('data della rottura del livello di fibonacci: '+str(history_m15[index]['Date']))
                                                print('signal: '+str(trade_setup[-1]))
                                                update_trade_in_progress(trade_setup[-1]['pair'], index, history_m15[index]['Date'])
                                                break

                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidLow'] <= get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)):
                                                print('trade chiuso per aver raggiunto il target senza retest')
                                                close_trade_in_retest(str_instrument)
                                                watchlist.append(':ballot_box_with_check: trade chiuso per aver raggiunto il target senza retest: '+str_instrument)
                                                break
                                            
                                            elif (pattern_breaking == True and 
                                                history_m15[index]['BidLow'] < pattern_breaking_candle_low):
                                                    pattern_breaking_candle_low = history_m15[index]['BidLow']
                                                    fib_78_6 = fibonacci_78_6(lasthigh, pattern_breaking_candle_low)

                                                    ###################
                                                    stop_loss_price = calculate_stop_loss_SHORT(str_instrument,pattern_rectY1, lasthigh)
                                                    target_price = get_nearest_lower_kijun_h4(history_m15[index], kijun_h4)
                                                    risk_reward = calculate_risk_reward_ratio(fib_78_6, target_price, stop_loss_price)
                                                    if risk_reward >= 2:
                                                        trade_setup.append({'pair': str_instrument, 
                                                                        'entry_price': fib_78_6, 
                                                                        'stop_loss_price':stop_loss_price, 
                                                                        'target_price': target_price, 
                                                                        'direction': 'SHORT', 
                                                                        'type': 'FULL',
                                                                        'risk_reward': risk_reward, 
                                                                        'zones_rectX1_DLY': str(zones_rectX1_DLY[dly_zone]),
                                                                        'zones_rectY1_DLY': zones_rectY1_DLY[dly_zone],
                                                                        'zones_rectY2_DLY': zones_rectY2_DLY[dly_zone],
                                                                        'zones_rectX1_H4': str(zones_rectX1_H4[h4_zone]),
                                                                        'zones_rectY1_H4': zones_rectY1_H4[h4_zone], 
                                                                        'zones_rectY2_H4': zones_rectY2_H4[h4_zone],
                                                                        'pattern_x1': str(pattern_rectX1),
                                                                        'pattern_y1': pattern_rectY1,
                                                                        'pattern_y2': pattern_rectY2,
                                                                        'breakup_date':history_m15[index]['Date'],
                                                                        'fibonacci100':lasthigh})
                                                    
                                                        target_1_1 = calculate_target_price_SHORT(trade_setup[-1]['entry_price'], trade_setup[-1]['stop_loss_price'], 1)
                                                        upsert_order_waiting_retest(trade_setup[-1], target_1_1)

                                                    else:
                                                        print('NO R:R')
                                                        watchlist.append(':ballot_box_with_check: pattern senza R:R valido: '+str_instrument)
                                                        mt5_close_order(str_instrument) #if there was a previous order placed in retest.
                                                        close_trade_in_retest(str_instrument)
                                                        break
                                                    ###################
                                        
                    ######## process trade in progress ########
                    trade_in_progress = check_in_progress_trade(str_instrument)
                    if trade_in_progress is not None:
                        #remove the same trades in close state
                        remove_closed_trades(str_instrument, trade_in_progress['entry_date'], trade_in_progress['pattern_x1'],trade_in_progress['pattern_y1'],trade_in_progress['pattern_y2'])
                        print('trade_in_progress:')
                        if trade_in_progress['direction'] == 'SHORT':
                            #print('trade_in_progress: '+str(trade_in_progress['stop_loss'])+' - '+str(trade_in_progress['entry_price_index']))
                            continue_logic, enddate = process_trades_SHORT(history_DLY, trade_in_progress['zones_recty1_dly'], history_m15, str_instrument, trade_in_progress['entry_price_index']+1, kijun_h4, trade_in_progress['stop_loss'], trade_in_progress['stop_loss'], trade_in_progress['entry_price'], trade_in_progress['target'], trade_in_progress['zones_recty1_h4'], history_H4, trade_in_progress['entry_date'])
                        if trade_in_progress['direction'] == 'LONG':
                            continue_logic, enddate = process_trades_LONG(history_DLY, trade_in_progress['zones_recty1_dly'], history_m15, str_instrument, trade_in_progress['entry_price_index']+1, kijun_h4, trade_in_progress['stop_loss'], trade_in_progress['stop_loss'], trade_in_progress['entry_price'], trade_in_progress['target'], trade_in_progress['zones_recty1_h4'], history_H4, trade_in_progress['entry_date'])                                 
                            
                                
                    if len(watchlist) != 0:
                        send_slack_message('mt-bot',watchlist[-1])
                
                #close mt5 orders already processed
                clean_trades()
                

        except Exception as e:
            common_samples.print_exception(e)
        try:
            fx.logout()
        except Exception as e:
            common_samples.print_exception(e)

if __name__ == "__main__":
    main()
    print("")
    #input("Done! Press enter key to exit\n")