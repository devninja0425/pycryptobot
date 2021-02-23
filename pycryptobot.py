"""Python Crypto Bot consuming Coinbase Pro or Binance APIs"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging, os, random, sched, sys, time

from models.PyCryptoBot import PyCryptoBot
from models.Trading import TechnicalAnalysis
from models.TradingAccount import TradingAccount
from models.CoinbasePro import AuthAPI, PublicAPI
from views.TradingGraphs import TradingGraphs

app = PyCryptoBot()

# initial state is to wait
action = 'WAIT'
last_action = ''
last_df_index = ''
buy_state = ''
last_buy = 0
iterations = 0
buy_count = 0
sell_count = 0
buy_sum = 0
sell_sum = 0

config = {}
account = None
# if live trading is enabled
if app.isLive() == 1:
    account = TradingAccount(app)

    # if the bot is restarted between a buy and sell it will sell first
    if (app.getMarket().startswith('BTC-') and account.getBalance(app.getBaseCurrency()) > 0.001):
        last_action = 'BUY'
    elif (app.getMarket().startswith('BCH-') and account.getBalance(app.getBaseCurrency()) > 0.01):
        last_action = 'BUY'
    elif (app.getMarket().startswith('ETH-') and account.getBalance(app.getBaseCurrency()) > 0.01):
        last_action = 'BUY'
    elif (app.getMarket().startswith('LTC-') and account.getBalance(app.getBaseCurrency()) > 0.1):
        last_action = 'BUY'
    elif (app.getMarket().startswith('XLM-') and account.getBalance(app.getBaseCurrency()) > 35):
        last_action = 'BUY'
    elif (account.getBalance(app.getQuoteCurrency()) > 30):
        last_action = 'SELL'

    orders = account.getOrders(app.getMarket(), '', 'done')
    if len(orders) > 0:
        df = orders[-1:]
        price = df[df.action == 'buy']['price']
        if len(price) > 0:
            last_buy = float(app.truncate(price, 2))

def executeJob(sc, market, granularity, tradingData=pd.DataFrame()):
    """Trading bot job which runs at a scheduled interval"""
    global action, buy_count, buy_sum, iterations, last_action, last_buy, last_df_index, sell_count, sell_sum, buy_state

    # increment iterations
    iterations = iterations + 1

    if app.isSimulation() == 0:
        # retrieve the app.getMarket() data
        tradingData = app.getHistoricalData(app.getMarket(), granularity)

    # analyse the market data
    tradingDataCopy = tradingData.copy()
    technicalAnalysis = TechnicalAnalysis(tradingDataCopy)
    technicalAnalysis.addAll()
    df = technicalAnalysis.getDataFrame()

    if len(df) != 300:
        # data frame should have 300 rows, if not retry
        print('error: data frame length is < 300 (' + str(len(df)) + ')')
        logging.error('error: data frame length is < 300 (' + str(len(df)) + ')')
        s.enter(300, 1, executeJob, (sc, market, granularity))

    if app.isSimulation() == 1:
        # with a simulation df_last will iterate through data
        df_last = df.iloc[iterations-1:iterations]
    else:
        # df_last contains the most recent entry
        df_last = df.tail(1)
 
    current_df_index = str(df_last.index.format()[0])

    if app.isSimulation() == 0:
        price = app.getTicker(market)
        if price < df_last['low'].values[0] or price == 0:
            price = float(df_last['close'].values[0])
    else:
        price = float(df_last['close'].values[0])

    # technical indicators
    ema12gtema26 = bool(df_last['ema12gtema26'].values[0])
    ema12gtema26co = bool(df_last['ema12gtema26co'].values[0])
    goldencross = bool(df_last['goldencross'].values[0])
    deathcross = bool(df_last['deathcross'].values[0])
    macdgtsignal = bool(df_last['macdgtsignal'].values[0])
    macdgtsignalco = bool(df_last['macdgtsignalco'].values[0])
    ema12ltema26 = bool(df_last['ema12ltema26'].values[0])
    ema12ltema26co = bool(df_last['ema12ltema26co'].values[0])
    macdltsignal = bool(df_last['macdltsignal'].values[0])
    macdltsignalco = bool(df_last['macdltsignalco'].values[0])

    # candlestick detection
    hammer = bool(df_last['hammer'].values[0])
    inverted_hammer = bool(df_last['inverted_hammer'].values[0])
    hanging_man = bool(df_last['hanging_man'].values[0])
    shooting_star = bool(df_last['shooting_star'].values[0])
    three_white_soldiers = bool(df_last['three_white_soldiers'].values[0])
    three_black_crows = bool(df_last['three_black_crows'].values[0])
    morning_star = bool(df_last['morning_star'].values[0])
    evening_star = bool(df_last['evening_star'].values[0])
    three_line_strike = bool(df_last['three_line_strike'].values[0])
    abandoned_baby = bool(df_last['abandoned_baby'].values[0])
    morning_doji_star = bool(df_last['morning_doji_star'].values[0])
    evening_doji_star = bool(df_last['evening_doji_star'].values[0])
    two_black_gapping = bool(df_last['two_black_gapping'].values[0])

    # criteria for a buy signal
    if ema12gtema26co == True and macdgtsignal == True and goldencross == True and last_action != 'BUY':
        action = 'BUY'
    # criteria for a sell signal
    elif ema12ltema26co == True and macdltsignal == True and last_action not in ['','SELL']:
        action = 'SELL'
    # anything other than a buy or sell, just wait
    else:
        action = 'WAIT'
    
    if last_buy > 0 and last_action == 'BUY':
        change_pcnt = ((price / last_buy) - 1) * 100

        # loss failsafe sell at sell_lower_pcnt
        if app.sellLowerPcnt() != None and change_pcnt < app.sellLowerPcnt():
            action = 'SELL'
            last_action = 'BUY'
            log_text = '! Loss Failsafe Triggered (< ' + str(app.sellLowerPcnt()) + '%)'
            print (log_text, "\n")
            logging.warning(log_text)

        # profit bank at sell_upper_pcnt
        if app.sellUpperPcnt() != None and change_pcnt > app.sellUpperPcnt():
            action = 'SELL'
            last_action = 'BUY'
            log_text = '! Profit Bank Triggered (> ' + str(app.sellUpperPcnt()) + '%)'
            print (log_text, "\n")
            logging.warning(log_text)

    goldendeathtext = ''
    if goldencross == True:
        goldendeathtext = ' (BULL)'
    elif deathcross == False:
        goldendeathtext = ' (BEAR)'

    # polling is every 5 minutes (even for hourly intervals), but only process once per interval
    if (last_df_index != current_df_index):
        precision = 2
        if app.getBaseCurrency() == 'XLM':
            precision = 4

        price_text = 'Close: ' + str(app.truncate(price, precision))
        ema_text = app.compare(df_last['ema12'].values[0], df_last['ema26'].values[0], 'EMA12/26', precision)
        macd_text = app.compare(df_last['macd'].values[0], df_last['signal'].values[0], 'MACD', precision)

        if hammer == True:
            log_text = '* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if shooting_star == True:
            log_text = '* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        if hanging_man == True:
            log_text = '* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        if inverted_hammer == True:
            log_text = '* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)
 
        if three_white_soldiers == True:
            log_text = '*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if three_black_crows == True:
            log_text = '* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        if morning_star == True:
            log_text = '*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if evening_star == True:
            log_text = '*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        if three_line_strike == True:
            log_text = '** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if abandoned_baby == True:
            log_text = '** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if morning_doji_star == True:
            log_text = '** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")'
            print (log_text, "\n")
            logging.debug(log_text)

        if evening_doji_star == True:
            log_text = '** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        if two_black_gapping == True:
            log_text = '*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")'
            print (log_text, "\n")
            logging.debug(log_text)

        ema_co_prefix = ''
        ema_co_suffix = ''
        if ema12gtema26co == True:
            ema_co_prefix = '*^ '
            ema_co_suffix = ' ^*'
        elif ema12ltema26co == True:
            ema_co_prefix = '*v '
            ema_co_suffix = ' v*'   
        elif ema12gtema26 == True:
            ema_co_prefix = '^ '
            ema_co_suffix = ' ^'
        elif ema12ltema26 == True:
            ema_co_prefix = 'v '
            ema_co_suffix = ' v'

        macd_co_prefix = ''
        macd_co_suffix = ''
        if macdgtsignalco == True:
            macd_co_prefix = '*^ '
            macd_co_suffix = ' ^*'
        elif macdltsignalco == True:
            macd_co_prefix = '*v '
            macd_co_suffix = ' v*'
        elif macdgtsignal == True:
            macd_co_prefix = '^ '
            macd_co_suffix = ' ^'
        elif macdltsignal == True:
            macd_co_prefix = 'v '
            macd_co_suffix = ' v'

        if app.isVerbose() == 0:
            if last_action != '':
                output_text = current_df_index + ' | ' + market + goldendeathtext + ' | ' + str(granularity) + ' | ' + price_text + ' | ' + ema_co_prefix + ema_text + ema_co_suffix + ' | ' + macd_co_prefix + macd_text + macd_co_suffix + ' | ' + action + ' ' + ' | Last Action: ' + last_action
            else:
                output_text = current_df_index + ' | ' + market + goldendeathtext + ' | ' + str(granularity) + ' | ' + price_text + ' | ' + ema_co_prefix + ema_text + ema_co_suffix + ' | ' + macd_co_prefix + macd_text + macd_co_suffix + ' | ' + action + ' '

            if last_action == 'BUY':
                # calculate last buy minus fees
                fee = last_buy * 0.005
                last_buy_minus_fees = last_buy + fee

                margin = str(app.truncate((((price - last_buy_minus_fees) / price) * 100), 2)) + '%'
                output_text += ' | ' +  margin

            logging.debug(output_text)
            print (output_text)
        else:
            logging.debug('-- Iteration: ' + str(iterations) + ' --' + goldendeathtext)

            if last_action == 'BUY':
                margin = str(app.truncate((((price - last_buy) / price) * 100), 2)) + '%'
                logging.debug('-- Margin: ' + margin + '% --')            
            
            logging.debug('price: ' + str(app.truncate(price, 2)))
            logging.debug('ema12: ' + str(app.truncate(float(df_last['ema12'].values[0]), 2)))
            logging.debug('ema26: ' + str(app.truncate(float(df_last['ema26'].values[0]), 2)))
            logging.debug('ema12gtema26co: ' + str(ema12gtema26co))
            logging.debug('ema12gtema26: ' + str(ema12gtema26))
            logging.debug('ema12ltema26co: ' + str(ema12ltema26co))
            logging.debug('ema12ltema26: ' + str(ema12ltema26))
            logging.debug('macd: ' + str(app.truncate(float(df_last['macd'].values[0]), 2)))
            logging.debug('signal: ' + str(app.truncate(float(df_last['signal'].values[0]), 2)))
            logging.debug('macdgtsignal: ' + str(macdgtsignal))
            logging.debug('macdltsignal: ' + str(macdltsignal))
            logging.debug('action: ' + action)

            # informational output on the most recent entry  
            print('')
            print('================================================================================')
            txt = '        Iteration : ' + str(iterations) + goldendeathtext
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '        Timestamp : ' + str(df_last.index.format()[0])
            print('|', txt, (' ' * (75 - len(txt))), '|')
            print('--------------------------------------------------------------------------------')
            txt = '            Close : ' + str(app.truncate(price, 2))
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '            EMA12 : ' + str(app.truncate(float(df_last['ema12'].values[0]), 2))
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '            EMA26 : ' + str(app.truncate(float(df_last['ema26'].values[0]), 2))
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '   Crossing Above : ' + str(ema12gtema26co)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '  Currently Above : ' + str(ema12gtema26)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '   Crossing Below : ' + str(ema12ltema26co)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '  Currently Below : ' + str(ema12ltema26)
            print('|', txt, (' ' * (75 - len(txt))), '|')

            if (ema12gtema26 == True and ema12gtema26co == True):
                txt = '        Condition : EMA12 is currently crossing above EMA26'
            elif (ema12gtema26 == True and ema12gtema26co == False):
                txt = '        Condition : EMA12 is currently above EMA26 and has crossed over'
            elif (ema12ltema26 == True and ema12ltema26co == True):
                txt = '        Condition : EMA12 is currently crossing below EMA26'
            elif (ema12ltema26 == True and ema12ltema26co == False):
                txt = '        Condition : EMA12 is currently below EMA26 and has crossed over'
            else:
                txt = '        Condition : -'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            print('--------------------------------------------------------------------------------')
            txt = '             MACD : ' + str(app.truncate(float(df_last['macd'].values[0]), 2))
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '           Signal : ' + str(app.truncate(float(df_last['signal'].values[0]), 2))
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '  Currently Above : ' + str(macdgtsignal)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '  Currently Below : ' + str(macdltsignal)
            print('|', txt, (' ' * (75 - len(txt))), '|')

            if (macdgtsignal == True and macdgtsignalco == True):
                txt = '        Condition : MACD is currently crossing above Signal'
            elif (macdgtsignal == True and macdgtsignalco == False):
                txt = '        Condition : MACD is currently above Signal and has crossed over'
            elif (macdltsignal == True and macdltsignalco == True):
                txt = '        Condition : MACD is currently crossing below Signal'
            elif (macdltsignal == True and macdltsignalco == False):
                txt = '        Condition : MACD is currently below Signal and has crossed over'
            else:
                txt = '        Condition : -'
            print('|', txt, (' ' * (75 - len(txt))), '|')

            print('--------------------------------------------------------------------------------')
            txt = '           Action : ' + action
            print('|', txt, (' ' * (75 - len(txt))), '|')
            print('================================================================================')
            if last_action == 'BUY':
                txt = '           Margin : ' + margin + '%'
                print('|', txt, (' ' * (75 - len(txt))), '|')
                print('================================================================================')

        # if a buy signal
        if action == 'BUY':
            last_buy = price
            buy_count = buy_count + 1
            fee = float(price) * 0.005
            price_incl_fees = float(price) + fee
            buy_sum = buy_sum + price_incl_fees

            # if live
            if app.isLive() == 1:
                if app.isVerbose() == 0:
                    logging.info(current_df_index + ' | ' + market + ' ' + str(granularity) + ' | ' + price_text + ' | BUY')
                    print ("\n", current_df_index, '|', market, granularity, '|', price_text, '| BUY', "\n")                    
                else:
                    print('--------------------------------------------------------------------------------')
                    print('|                      *** Executing LIVE Buy Order ***                        |')
                    print('--------------------------------------------------------------------------------')
                
                # execute a live market buy
                resp = app.marketBuy(market, float(account.getBalance(app.getQuoteCurrency())))
                logging.info(resp)

            # if not live
            else:
                if app.isVerbose() == 0:
                    logging.info(current_df_index + ' | ' + market + ' ' + str(granularity) + ' | ' + price_text + ' | BUY')
                    print ("\n", current_df_index, '|', market, granularity, '|', price_text, '| BUY')
                    print (' Fibonacci Retracement Levels:', str(technicalAnalysis.getFibonacciRetracementLevels(float(price))), "\n")                    
                else:
                    print('--------------------------------------------------------------------------------')
                    print('|                      *** Executing TEST Buy Order ***                        |')
                    print('--------------------------------------------------------------------------------')

            if app.shouldSaveGraphs() == 1:
                tradinggraphs = TradingGraphs(technicalAnalysis)
                ts = datetime.now().timestamp()
                filename = app.getMarket() + '_' + str(app.getGranularity()) + '_buy_' + str(ts) + '.png'
                tradinggraphs.renderEMAandMACD(24, 'graphs/' + filename, True)

        # if a sell signal
        elif action == 'SELL':
            sell_count = sell_count + 1
            fee = float(price) * 0.005
            price_incl_fees = float(price) - fee
            sell_sum = sell_sum + price_incl_fees

            # if live
            if app.isLive() == 1:
                if app.isVerbose() == 0:
                    logging.info(current_df_index + ' | ' + market + ' ' + str(granularity) + ' | ' + price_text + ' | SELL')
                    print ("\n", current_df_index, '|', market, granularity, '|', price_text, '| SELL')
                    print (' Fibonacci Retracement Levels:', str(technicalAnalysis.getFibonacciRetracementLevels(float(price))), "\n")                      
                else:
                    print('--------------------------------------------------------------------------------')
                    print('|                      *** Executing LIVE Sell Order ***                        |')
                    print('--------------------------------------------------------------------------------')

                # execute a live market sell
                resp = app.marketSell(market, float(account.getBalance(app.getBaseCurrency())))
                logging.info(resp)

            # if not live
            else:
                if app.isVerbose() == 0:
                    sell_price = float(str(app.truncate(price, precision)))
                    last_buy_price = float(str(app.truncate(float(last_buy), precision)))
                    buy_sell_diff = round(np.subtract(sell_price, last_buy_price), precision)
                    buy_sell_margin_no_fees = str(app.truncate((((sell_price - last_buy_price) / sell_price) * 100), 2)) + '%'

                    # calculate last buy minus fees
                    buy_fee = last_buy_price * 0.005
                    last_buy_price_minus_fees = last_buy_price + buy_fee

                    buy_sell_margin_fees = str(app.truncate((((sell_price - last_buy_price_minus_fees) / sell_price) * 100), 2)) + '%'

                    logging.info(current_df_index + ' | ' + market + ' ' + str(granularity) + ' | SELL | ' + str(sell_price) + ' | BUY | ' + str(last_buy_price) + ' | DIFF | ' + str(buy_sell_diff) + ' | MARGIN NO FEES | ' + str(buy_sell_margin_no_fees) + ' | MARGIN FEES | ' + str(buy_sell_margin_fees))
                    print ("\n", current_df_index, '|', market, granularity, '| SELL |', str(sell_price), '| BUY |', str(last_buy_price), '| DIFF |', str(buy_sell_diff) , '| MARGIN NO FEES |', str(buy_sell_margin_no_fees), '| MARGIN FEES |', str(buy_sell_margin_fees), "\n")                    
                else:
                    print('--------------------------------------------------------------------------------')
                    print('|                      *** Executing TEST Sell Order ***                        |')
                    print('--------------------------------------------------------------------------------')

            if app.shouldSaveGraphs() == 1:
                tradinggraphs = TradingGraphs(technicalAnalysis)
                ts = datetime.now().timestamp()
                filename = app.getMarket() + '_' + str(app.getGranularity()) + '_buy_' + str(ts) + '.png'
                tradinggraphs.renderEMAandMACD(24, 'graphs/' + filename, True)

        # last significant action
        if action in ['BUY','SELL']:
            last_action = action
        
        last_df_index = str(df_last.index.format()[0])

        if iterations == 300:
            print ("\nSimulation Summary\n")

            if buy_count > sell_count:
                fee = last_buy * 0.005
                last_buy_minus_fees = last_buy + fee
                buy_sum = buy_sum + (float(app.truncate(price, precision)) - last_buy_minus_fees)

            print ('   Buy Count :', buy_count)
            print ('  Sell Count :', sell_count, "\n")
            print ('      Margin :', str(app.truncate((((sell_sum - buy_sum) / sell_sum) * 100), 2)) + '%', "\n")
    else:
        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        print (now, '|', market + goldendeathtext, '|', str(granularity), '| Current Price:', price)

        # decrement ignored iteration
        iterations = iterations - 1

    # if live
    if app.isLive() == 1:
        # update order tracker csv
        account.saveTrackerCSV()

    if app.isSimulation() == 1:
        if iterations < 300:
            if app.simuluationSpeed() in [ 'fast', 'fast-sample' ]:
                # fast processing
                executeJob(sc, market, granularity, tradingData)
            else:
                # slow processing
                s.enter(1, 1, executeJob, (sc, market, granularity, tradingData))

    else:
        # poll every 5 minute
        s.enter(300, 1, executeJob, (sc, market, granularity))

try:
    logging.basicConfig(filename='pycryptobot.log', format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filemode='a', level=logging.DEBUG)

    print('--------------------------------------------------------------------------------')
    print('|           Python Crypto Bot using the Coinbase Pro or Binanace APIs          |')
    print('--------------------------------------------------------------------------------')

    if app.isVerbose() == 1:   
        txt = '           Market : ' + app.getMarket()
        print('|', txt, (' ' * (75 - len(txt))), '|')
        txt = '      Granularity : ' + str(app.getGranularity()) + ' seconds'
        print('|', txt, (' ' * (75 - len(txt))), '|')
        print('--------------------------------------------------------------------------------')

    if app.isLive() == 1:
        txt = '         Bot Mode : LIVE - live trades using your funds!'
    else:
        txt = '         Bot Mode : TEST - test trades using dummy funds :)'

    print('|', txt, (' ' * (75 - len(txt))), '|')

    txt = '      Bot Started : ' + str(datetime.now())
    print('|', txt, (' ' * (75 - len(txt))), '|')
    print('================================================================================')
    if app.sellUpperPcnt() != None:
        txt = '       Sell Upper : ' + str(app.sellUpperPcnt()) + '%'
        print('|', txt, (' ' * (75 - len(txt))), '|')
    
    if app.sellUpperPcnt() != None:
        txt = '       Sell Lower : ' + str(app.sellLowerPcnt()) + '%'
        print('|', txt, (' ' * (75 - len(txt))), '|')

    if app.sellUpperPcnt() != None and app.sellLowerPcnt() != None:
        print('================================================================================')

    # if live
    if app.isLive() == 1:
        # if live, ensure sufficient funds to place next buy order
        if (last_action == '' or last_action == 'SELL') and account.getBalance(app.getQuoteCurrency()) == 0:
            raise Exception('Insufficient ' + app.getQuoteCurrency() + ' funds to place next buy order!')
        # if live, ensure sufficient crypto to place next sell order
        elif last_action == 'BUY' and account.getBalance(app.getBaseCurrency()) == 0:
            raise Exception('Insufficient ' + app.getBaseCurrency() + ' funds to place next sell order!')

    s = sched.scheduler(time.time, time.sleep)
    # run the first job immediately after starting
    if app.isSimulation() == 1:
        if app.simuluationSpeed() in [ 'fast-sample', 'slow-sample' ]:
            tradingData = pd.DataFrame()

            attempts = 0
            while len(tradingData) != 300 and attempts < 10:
                endDate = datetime.now() - timedelta(hours=random.randint(0,8760 * 3)) # 3 years in hours
                startDate = endDate - timedelta(hours=300)
                tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity(), startDate.isoformat(), endDate.isoformat())
                attempts += 1

            if len(tradingData) != 300:
                raise Exception('Unable to retrieve 300 random sets of data between ' + str(startDate) + ' and ' + str(endDate) + ' in ' + str(attempts) + ' attempts.')

            startDate = str(startDate.isoformat())
            endDate = str(endDate.isoformat())
            txt = '   Sampling start : ' + str(startDate)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            txt = '     Sampling end : ' + str(endDate)
            print('|', txt, (' ' * (75 - len(txt))), '|')
            print('================================================================================')
        else:
            tradingData = app.getHistoricalData(app.getMarket(), app.getGranularity())

        executeJob(s, app.getMarket(), app.getGranularity(), tradingData)
    else: 
        executeJob(s, app.getMarket(), app.getGranularity())
    
    s.run()

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    print(datetime.now(), 'closed')
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)