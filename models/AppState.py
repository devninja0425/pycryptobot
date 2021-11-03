"""Application state class"""

import sys
import datetime
from numpy import array as np_array, min as np_min, ptp as np_ptp
from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.coinbase_pro import AuthAPI as CAuthAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI
from models.helper.LogHelper import Logger


class AppState:
    def __init__(self, app: PyCryptoBot, account: TradingAccount) -> None:
        if app.getExchange() == "binance":
            self.api = BAuthAPI(
                app.getAPIKey(),
                app.getAPISecret(),
                app.getAPIURL(),
                recv_window=app.getRecvWindow(),
            )
        elif app.getExchange() == "coinbasepro":
            self.api = CAuthAPI(
                app.getAPIKey(),
                app.getAPISecret(),
                app.getAPIPassphrase(),
                app.getAPIURL(),
            )
        elif app.getExchange() == "kucoin":
            self.api = KAuthAPI(
                app.getAPIKey(),
                app.getAPISecret(),
                app.getAPIPassphrase(),
                app.getAPIURL(),
            )
        else:
            self.api = None

        self.app = app
        self.account = account

        self.action = "WAIT"
        self.buy_count = 0
        self.buy_state = ""
        self.buy_sum = 0
        self.eri_text = ""
        self.fib_high = 0
        self.fib_low = 0
        self.first_buy_size = 0
        self.iterations = 0
        self.last_action = "WAIT"
        self.last_buy_size = 0
        self.last_buy_price = 0
        self.last_buy_filled = 0
        self.last_buy_fee = 0
        self.last_buy_high = 0
        self.last_sell_size = 0
        self.last_df_index = ""
        self.sell_count = 0
        self.sell_sum = 0

        self.margintracker = 0
        self.profitlosstracker = 0
        self.feetracker = 0
        self.buy_tracker = 0

        self.last_api_call_datetime = datetime.datetime.now() - datetime.timedelta(minutes=2)
        self.exchange_last_buy = None

    def minimumOrderBase(self):
        self.app.insufficientfunds = False
        if self.app.getExchange() == "binance":
            df = self.api.getMarketInfoFilters(self.app.getMarket())

            if len(df) > 0:
                try:
                    base_min = float(
                        df[df["filterType"] == "LOT_SIZE"][["minQty"]].values[0][0]
                    )
                    base = float(self.account.basebalance)
                except:
                    return

                if base < base_min:
                    if self.app.enableinsufficientfundslogging:
                        self.app.insufficientfunds = True
                        Logger.warning(f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})")
                        return

                    sys.tracebacklimit = 0
                    raise Exception(
                        f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})"
                    )

                return

        elif self.app.getExchange() == "coinbasepro":
            product = self.api.authAPI("GET", f"products/{self.app.getMarket()}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.getMarket()})")

            base = float(self.account.basebalance)
            base_min = float(product["base_min_size"])

        elif self.app.getExchange() == 'kucoin':
            resp = self.api.authAPI('GET', f'api/v1/symbols')
            product = resp[resp['symbol'] == self.app.getMarket()]
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f'Market not found! ({self.app.getMarket()})')

            base = float(self.account.basebalance)
            base_min = float(product['baseMinSize'])
            # additional check for last order type
            if base > base_min: 
                return True

        if base < base_min:
            if self.app.enableinsufficientfundslogging:
                self.app.insufficientfunds = True
                Logger.warning(f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})")
                return
                        
            sys.tracebacklimit = 0
            raise Exception(
                f"Insufficient Base Funds! (Actual: {base}, Minimum: {base_min})"
            )
            
    def minimumOrderQuote(self):
        self.app.insufficientfunds = False
        if self.app.getExchange() == "binance":
            df = self.api.getMarketInfoFilters(self.app.getMarket())

            if len(df) > 0:
                try:
                    quote_min = float(
                        df[df["filterType"] == "MIN_NOTIONAL"][["minNotional"]].values[
                            0
                        ][0]
                    )
                    quote = float(self.account.quotebalance)
                except:
                    return

                if quote < quote_min:
                    if self.app.enableinsufficientfundslogging:
                        self.app.insufficientfunds = True
                        Logger.warning(f"Insufficient Quote Funds! (Actual: {quote}, Minimum: {quote_min})")
                        return

                    sys.tracebacklimit = 0
                    raise Exception(
                        f"Insufficient Quote Funds! (Actual: {quote}, Minimum: {quote_min})"
                    )
                return
            else:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.getMarket()})")

        elif self.app.getExchange() == "coinbasepro":
            product = self.api.authAPI("GET", f"products/{self.app.getMarket()}")
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f"Market not found! ({self.app.getMarket()})")

            ticker = self.api.authAPI("GET", f"products/{self.app.getMarket()}/ticker")
            price = float(ticker["price"])

            quote = float(self.account.quotebalance)
            base_min = float(product["base_min_size"])

        elif self.app.getExchange() == 'kucoin':
            resp = self.api.authAPI('GET', f'api/v1/symbols')
            product = resp[resp['symbol'] == self.app.getMarket()]
            if len(product) == 0:
                sys.tracebacklimit = 0
                raise Exception(f'Market not found! ({self.app.getMarket()})')

            ticker = self.api.authAPI("GET", f"api/v1/market/orderbook/level1?symbol={self.app.getMarket()}")

            price = float(ticker["price"])
            quote = float(self.account.quotebalance)
            base_min = float(product['baseMinSize'])
            # additional check for last order type
            if (quote / price) > base_min: 
                return True

        if (quote / price) < base_min:
            if self.app.enableinsufficientfundslogging:
                self.app.insufficientfunds = True
                Logger.warning(f'Insufficient Quote Funds! (Actual: {"{:.8f}".format((quote / price))}, Minimum: {base_min})')
                return
                    
            sys.tracebacklimit = 0
            raise Exception(
                f'Insufficient Quote Funds! (Actual: {"{:.8f}".format((quote / price))}, Minimum: {base_min})'
            )

    def getLastOrder(self):
        # if not live
        if not self.app.isLive():
            self.last_action = "SELL"
            return

        base = float(self.account.getBalance(self.app.getBaseCurrency()))
        quote = float(self.account.getBalance(self.app.getQuoteCurrency()))
        #base = float(self.account.basebalance)
        #quote = float(self.account.quotebalance)

        orders = self.account.getOrders(self.app.getMarket(), "", "done")
        if len(orders) > 0:
            last_order = orders[-1:]

            # if orders exist and last order is a buy
            if str(last_order.action.values[0]) == "buy" and base > 0.0:
                self.last_buy_size = float(
                    last_order[last_order.action == "buy"]["size"]
                )
                self.last_buy_filled = float(
                    last_order[last_order.action == "buy"]["filled"]
                )
                self.last_buy_price = float(
                    last_order[last_order.action == "buy"]["price"]
                )

                # binance orders do not show fees
                if self.app.getExchange() == "coinbasepro" or self.app.getExchange() == "kucoin":
                    self.last_buy_fee = float(
                        last_order[last_order.action == "buy"]["fees"]
                    )

                self.last_action = "BUY"
                return
            else:
                self.minimumOrderQuote()
                self.last_action = "SELL"
                self.last_buy_price = 0.0
                return
        else:
            # nil base or quote funds
            if base == 0.0 and quote == 0.0:
                if self.app.enableinsufficientfundslogging:
                    self.app.insufficientfunds = True
                    Logger.warning(f"Insufficient Funds! ({self.app.getBaseCurrency()}={str(base)}, {self.app.getQuoteCurrency()}={str(base)})")
                    self.last_action = "WAIT"
                    return

                sys.tracebacklimit = 0
                raise Exception(
                    f"Insufficient Funds! ({self.app.getBaseCurrency()}={str(base)}, {self.app.getQuoteCurrency()}={str(base)})"
                )

            # determine last action by comparing normalised [0,1] base and quote balances
            order_pairs = np_array([base, quote])
            order_pairs_normalised = (order_pairs - np_min(order_pairs)) / np_ptp(
                order_pairs
            )

            # If Kucoin returns emoty response, on a shared trading account, could multiple buy same pair
            if self.app.getExchange() == "kucoin" and self.minimumOrderBase() and self.minimumOrderQuote():
                if self.last_action == "BUY":
                    return
                else:
                self.last_action = "WAIT"
                Logger.warning('Kucoin temporary state set to "WAIT".') 
            elif order_pairs_normalised[0] < order_pairs_normalised[1]:
                self.minimumOrderQuote()
                self.last_action = "SELL"
            elif order_pairs_normalised[0] > order_pairs_normalised[1]:
                self.minimumOrderBase()
                self.last_action = "BUY"

            else:
                self.last_action = "WAIT"

            return

    def initLastAction(self):
        # ignore if manually set
        if self.app.getLastAction() is not None:
            self.last_action = self.app.getLastAction()
            return

        self.getLastOrder()

    def pollLastAction(self):
        self.getLastOrder()
