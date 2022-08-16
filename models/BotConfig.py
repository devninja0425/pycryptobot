import argparse
import json
import os
import re
import sys

import yaml
from yaml.constructor import ConstructorError
from yaml.scanner import ScannerError

from models.ConfigBuilder import ConfigBuilder
from models.chat import Telegram
from models.config import (
    binanceConfigParser,
    coinbaseProConfigParser,
    kucoinConfigParser,
    dummyConfigParser,
    loggerConfigParser,
)
from models.exchange.Granularity import Granularity
from models.exchange.ExchangesEnum import Exchange
from models.helper.LogHelper import Logger


class BotConfig:
    def __init__(self, *args, **kwargs):
        self.cli_args = self._parse_arguments()

        if self.cli_args["init"]:
            ConfigBuilder().init()
            sys.exit()

        self.configbuilder = False

        self.granularity = Granularity.ONE_HOUR
        self.base_currency = "BTC"
        self.quote_currency = "GBP"
        self.is_live = 0
        self.is_verbose = 0
        self.save_graphs = 0
        self.is_sim = 0
        self.simstart_date = None
        self.simend_date = None
        self.sim_speed = "fast"
        self.sell_upper_pcnt = None
        self.sell_lower_pcnt = None
        self.nosellminpcnt = None
        self.nosellmaxpcnt = None
        self.trailing_stop_loss = 0.0
        self.trailing_stop_loss_trigger = 0.0
        self.dynamic_tsl = False
        self.tsl_multiplier = 1.1
        self.tsl_trigger_multiplier = 1.1
        self.tsl_max_pcnt = float(-5)
        self.sell_at_loss = 1
        self.smart_switch = 1
        self.sell_smart_switch = 0
        self.preventloss = False
        self.preventlosstrigger = 1.0
        self.preventlossmargin = 0.1

        self.telegram = False

        self.logbuysellinjson = False
        self.telegramdatafolder = "."

        self.buypercent = 100
        self.sellpercent = 100
        self.last_action = None
        self._chat_client = None
        self.buymaxsize = None
        self.buyminsize = 0
        self.sellfullbaseamount = True

        self.buylastsellsize = False
        self.trailingbuypcnt = 0
        self.trailingimmediatebuy = False
        self.trailingbuyimmediatepcnt = None
        self.marketmultibuycheck = False

        self.trailingsellpcnt = 0.0
        self.trailingimmediatesell = False
        self.trailingsellimmediatepcnt = 0.0
        self.trailingsellbailoutpcnt = 0.0
        self.selltriggeroverride = False

        self.sellatresistance = False
        self.autorestart = False
        self.stats = False
        self.statgroup = None
        self.statstart_date = None
        self.statdetail = False
        self.nobuynearhighpcnt = 3
        self.simresultonly = False

        self.disablebullonly = False
        self.disablebuynearhigh = False
        self.disablebuymacd = False
        self.disablebuyema = False
        self.disablebuyobv = True
        self.disablebuyelderray = True
        self.disablefailsafefibonaccilow = False
        self.disablefailsafelowerpcnt = False
        self.disableprofitbankupperpcnt = False
        self.disableprofitbankreversal = False
        self.enable_pandas_ta = False
        self.enable_custom_strategy = False
        self.disabletelegram = False
        self.disablelog = False
        self.disabletracker = True
        self.enableml = False
        self.websocket = False
        self.enableexitaftersell = False
        self.use_sell_fee = True

        self.enableinsufficientfundslogging = False
        self.insufficientfunds = False
        self.enable_telegram_bot_control = False
        self.enableimmediatebuy = False

        self.telegramtradesonly = False
        self.disabletelegramerrormsgs = False

        self.filelog = True
        self.logfile = (
            self.cli_args["logfile"] if self.cli_args["logfile"] else "pycryptobot.log"
        )
        self.fileloglevel = "DEBUG"
        self.consolelog = True
        self.consoleloglevel = "INFO"

        self.ema1226_5m_cache = None
        self.ema1226_15m_cache = None
        self.ema1226_1h_cache = None
        self.ema1226_6h_cache = None
        self.sma50200_1h_cache = None

        self.ticker_date = None
        self.ticker_price = None
        self.df_data = list(range(0, 10))  # [0,1,2,3,4,5,6,7,8,9]

        self.sim_smartswitch = False

        self.usekucoincache = False
        self.adjusttotalperiods = 300
        self.manual_trades_only = False

        self.recv_window = self._set_recv_window()

        self.config_file = kwargs.get("config_file", "config.json")

        self.tradesfile = (
            self.cli_args["tradesfile"] if self.cli_args["tradesfile"] else "trades.csv"
        )

        self.config_provided = False
        self.config = {}

        if self.cli_args["config"] is not None:
            self.config_file = self.cli_args["config"]
            self.config_provided = True

        self.exchange = self._set_exchange(kwargs["exchange"])

        self.startmethod = (
            self.cli_args["startmethod"] if self.cli_args["startmethod"] else "standard"
        )
        self.enable_atr72_pcnt = True
        self.enable_buy_next = True
        self.enable_volume = False
        # print(self.startmethod)

        # set defaults
        (
            self.api_url,
            self.api_key,
            self.api_secret,
            self.api_passphrase,
            self.market,
        ) = self._set_default_api_info(self.exchange)

        self.read_config(kwargs["exchange"])

        Logger.configure(
            filelog=self.filelog,
            logfile=self.logfile,
            fileloglevel=self.fileloglevel,
            consolelog=self.consolelog,
            consoleloglevel=self.consoleloglevel,
        )

    # read and set config from file
    def read_config(self, exchange):
        if os.path.isfile(self.config_file):
            self.config_provided = True
            try:
                with open(self.config_file, "r", encoding="utf8") as stream:
                    try:
                        self.config = yaml.safe_load(stream)
                    except Exception:
                        try:
                            stream.seek(0)
                            self.config = json.load(stream)
                        except json.decoder.JSONDecodeError as err:
                            sys.tracebacklimit = 0
                            raise ValueError(f"Invalid config.json: {str(err)}")

            except (ScannerError, ConstructorError) as err:
                sys.tracebacklimit = 0
                raise ValueError(
                    f"Invalid config: cannot parse config file: {str(err)}"
                )

            except (IOError, FileNotFoundError) as err:
                sys.tracebacklimit = 0
                raise ValueError(f"Invalid config: cannot open config file: {str(err)}")

            except ValueError as err:
                sys.tracebacklimit = 0
                raise ValueError(f"Invalid config: {str(err)}")

            except Exception:
                raise

            # set exchange platform
        self.exchange = self._set_exchange(exchange)  # set defaults
        (
            self.api_url,
            self.api_key,
            self.api_secret,
            self.api_passphrase,
            self.market,
        ) = self._set_default_api_info(self.exchange)

        if self.config_provided:
            if (
                self.exchange == Exchange.COINBASEPRO
                and self.exchange.value in self.config
            ):
                coinbaseProConfigParser(
                    self, self.config[self.exchange.value], self.cli_args
                )

            elif (
                self.exchange == Exchange.BINANCE and self.exchange.value in self.config
            ):
                binanceConfigParser(
                    self, self.config[self.exchange.value], self.cli_args
                )

            elif (
                self.exchange == Exchange.KUCOIN and self.exchange.value in self.config
            ):
                kucoinConfigParser(
                    self, self.config[self.exchange.value], self.cli_args
                )

            elif self.exchange == Exchange.DUMMY and self.exchange.value in self.config:
                dummyConfigParser(self, self.config[self.exchange.value], self.cli_args)

            if (
                not self.disabletelegram
                and "telegram" in self.config
                and "token" in self.config["telegram"]
                and "client_id" in self.config["telegram"]
            ):
                telegram = self.config["telegram"]
                self._chat_client = Telegram(telegram["token"], telegram["client_id"])
                if "datafolder" in telegram:
                    self.telegramdatafolder = telegram["datafolder"]
                self.telegram = True

            if "scanner" in self.config:
                self.enableexitaftersell = (
                    self.config["scanner"]["enableexitaftersell"]
                    if "enableexitaftersell" in self.config["scanner"]
                    else False
                )
                self.enable_buy_next = (
                    True
                    if "enable_buy_now" not in self.config["scanner"]
                    else self.config["scanner"]["enable_buy_now"]
                )
                self.enable_atr72_pcnt = (
                    True
                    if "enable_atr72_pcnt" not in self.config["scanner"]
                    else self.config["scanner"]["enable_atr72_pcnt"]
                )
                self.enable_volume = (
                    False
                    if "enable_volume" not in self.config["scanner"]
                    else self.config["scanner"]["enable_volume"]
                )

            if "logger" in self.config:
                loggerConfigParser(self, self.config["logger"])

            if self.disablelog:
                self.filelog = 0
                self.fileloglevel = "NOTSET"
                self.logfile == "/dev/null"

        else:
            if self.exchange == Exchange.BINANCE:
                binanceConfigParser(self, None, self.cli_args)
            elif self.exchange == Exchange.KUCOIN:
                kucoinConfigParser(self, None, self.cli_args)
            else:
                coinbaseProConfigParser(self, None, self.cli_args)

            self.filelog = 0
            self.fileloglevel = "NOTSET"
            self.logfile == "/dev/null"

    def _set_exchange(self, exchange: str = None) -> Exchange:
        if self.cli_args["exchange"] is not None:
            exchange = Exchange(self.cli_args["exchange"])

        if isinstance(exchange, str):
            exchange = Exchange(exchange)

        if not exchange:
            if (Exchange.COINBASEPRO.value or "api_pass") in self.config:
                exchange = Exchange.COINBASEPRO
            elif Exchange.BINANCE.value in self.config:
                exchange = Exchange.BINANCE
            elif Exchange.KUCOIN.value in self.config:
                exchange = Exchange.KUCOIN
            else:
                exchange = Exchange.DUMMY
        return exchange

    def _set_default_api_info(self, exchange: Exchange = Exchange.DUMMY) -> tuple:
        conf = {
            "binance": {
                "api_url": "https://api.binance.com",
                "api_key": "0000000000000000000000000000000000000000000000000000000000000000",
                "api_secret": "0000000000000000000000000000000000000000000000000000000000000000",
                "api_passphrase": "",
                "market": "BTCGBP",
            },
            "coinbasepro": {
                "api_url": "https://api.pro.coinbase.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
            "kucoin": {
                "api_url": "https://api.kucoin.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
            "dummy": {
                "api_url": "https://api.pro.coinbase.com",
                "api_key": "00000000000000000000000000000000",
                "api_secret": "0000/0000000000/0000000000000000000000000000000000000000000000000000000000/00000000000==",
                "api_passphrase": "00000000000",
                "market": "BTC-GBP",
            },
        }
        return (
            conf[exchange.value]["api_url"],
            conf[exchange.value]["api_key"],
            conf[exchange.value]["api_secret"],
            conf[exchange.value]["api_passphrase"],
            conf[exchange.value]["market"],
        )

    def get_version_from_readme(self) -> str:
        regex = r"^# Python Crypto Bot (v\d{1,3}\.\d{1,3}\.\d{1,3})"
        version = "v0.0.0"
        try:
            with open("README.md", "r", encoding="utf8") as stream:
                for line in stream:
                    match = re.search(regex, line)
                    try:
                        if match is None:
                            Logger.error("Could not find version in README.md")
                            sys.exit()

                        version = match.group(1)
                        break
                    except Exception:
                        continue

            if version == "v0.0.0":
                Logger.error("Could not find version in README.md")
                sys.exit()

            return version
        except Exception:
            raise

    def _set_recv_window(self):
        recv_window = 5000
        if self.cli_args["recvWindow"] and isinstance(self.cli_args["recvWindow"], int):
            if 5000 <= int(self.cli_args["recvWindow"]) <= 60000:
                recv_window = int(self.cli_args["recvWindow"])
            else:
                raise ValueError(
                    "recvWindow out of bounds! Should be between 5000 and 60000."
                )
        return recv_window

    def _parse_arguments(self):
        # instantiate the arguments parser
        parser = argparse.ArgumentParser(
            description="Python Crypto Bot using the Coinbase Pro or Binanace API"
        )

        # config builder
        parser.add_argument(
            "--init", action="store_true", help="config.json configuration builder"
        )

        # optional arguments
        parser.add_argument(
            "--exchange", type=str, help="'coinbasepro', 'binance', 'kucoin', 'dummy'"
        )
        parser.add_argument(
            "--granularity",
            type=str,
            help="coinbasepro: (60,300,900,3600,21600,86400), binance: (1m,5m,15m,1h,6h,1d), kucoin: (1min,3min,5min,15min,30min,1hour,6hour,1day)",
        )
        parser.add_argument(
            "--graphs", type=int, help="save graphs=1, do not save graphs=0"
        )
        parser.add_argument("--live", type=int, help="live=1, test=0")
        parser.add_argument(
            "--market",
            type=str,
            help="coinbasepro and kucoin: BTC-GBP, binance: BTCGBP etc.",
        )
        parser.add_argument(
            "--sellupperpcnt",
            type=float,
            help="optionally set sell upper percent limit",
        )
        parser.add_argument(
            "--selllowerpcnt",
            type=float,
            help="optionally set sell lower percent limit",
        )
        parser.add_argument(
            "--nosellminpcnt",
            type=float,
            help="optionally set minimum margin to not sell",
        )
        parser.add_argument(
            "--nosellmaxpcnt",
            type=float,
            help="optionally set maximum margin to not sell",
        )
        parser.add_argument(
            "--sim", type=str, help="simulation modes: fast, fast-sample, slow-sample"
        )
        parser.add_argument(
            "--simstart_date",
            type=str,
            help="start date for sample simulation e.g '2021-01-15'",
        )
        parser.add_argument(
            "--simend_date",
            type=str,
            help="end date for sample simulation e.g '2021-01-15' or 'now'",
        )
        parser.add_argument(
            "--smartswitch",
            type=int,
            help="optionally smart switch between 1 hour and 15 minute intervals",
        )
        parser.add_argument(
            "--verbose", type=int, help="verbose output=1, minimal output=0"
        )
        parser.add_argument(
            "--config",
            type=str,
            help="Use the config file at the given location. e.g 'myconfig.json'",
        )
        parser.add_argument(
            "--api_key_file",
            type=str,
            help="Use the API key file at the given location. e.g 'myapi.key'",
        )
        parser.add_argument(
            "--logfile",
            type=str,
            help="Use the log file at the given location. e.g 'mymarket.log'",
        )
        parser.add_argument(
            "--tradesfile",
            type=str,
            help="Path to file to log trades done during simulation. eg './trades/BTCBUSD-trades.csv",
        )
        parser.add_argument(
            "--buypercent", type=int, help="percentage of quote currency to buy"
        )
        parser.add_argument(
            "--sellpercent", type=int, help="percentage of base currency to sell"
        )
        parser.add_argument(
            "--lastaction", type=str, help="optionally set the last action (BUY, SELL)"
        )
        parser.add_argument("--buymaxsize", type=float, help="maximum size on buy")
        parser.add_argument("--buyminsize", type=float, help="minimum size on buy")

        parser.add_argument(
            "--buylastsellsize",
            type=int,
            help="1 = buy size of last sell, 0 = disabled",
        )
        parser.add_argument(
            "--trailingbuypcnt",
            type=float,
            help="percent of increase to wait before buying",
        )
        parser.add_argument(
            "--trailingimmediatebuy",
            action="store_true",
            help="immediate buy if trailingbuypcnt reached",
        )
        parser.add_argument(
            "--trailingbuyimmediatepcnt",
            type=float,
            help="percent of increase to trigger immediate buy",
        )
        parser.add_argument(
            "--marketmultibuycheck",
            action="store_true",
            help="additional check for market multiple buys",
        )

        # optional options
        parser.add_argument(
            "--autorestart",
            action="store_true",
            help="Auto restart the bot in case of exception",
        )
        parser.add_argument(
            "--stats", action="store_true", help="display summary of completed trades"
        )
        parser.add_argument(
            "--statgroup", nargs="+", help="add multiple currency pairs to merge stats"
        )
        parser.add_argument(
            "--statstart_date",
            type=str,
            help="trades before this date are ignored in stats function e.g 2021-01-15",
        )
        parser.add_argument(
            "--statdetail",
            action="store_true",
            help="display detail of completed transactions for a given market",
        )
        parser.add_argument(
            "--simresultonly",
            action="store_true",
            help="show simulation result only",
        )
        parser.add_argument(
            "--telegramtradesonly",
            action="store_true",
            help="Toggle Telegram trades only output",
        )
        parser.add_argument(
            "--disabletelegramerrormsgs",
            action="store_true",
            help="Disable Telegram error message output",
        )

        # disable defaults
        parser.add_argument(
            "--disablefailsafelowerpcnt",
            action="store_true",
            help="disable failsafe sell on 'selllowerpcnt'",
        )
        parser.add_argument(
            "--disableprofitbankupperpcnt",
            action="store_true",
            help="disable profit bank on 'sellupperpcnt'",
        )
        parser.add_argument(
            "--disableprofitbankreversal",
            action="store_true",
            help="disable profit bank on strong candlestick reversal",
        )
        parser.add_argument(
            "--disabletelegram", action="store_true", help="disable telegram messages"
        )
        parser.add_argument(
            "--disablelog", action="store_true", help="disable pycryptobot.log"
        )
        parser.add_argument(
            "--disabletracker", action="store_true", help="disable tracker.csv"
        )
        parser.add_argument(
            "--recvWindow",
            type=int,
            help="binance exchange api recvWindow, integer between 5000 and 60000",
        )
        parser.add_argument(
            "--enableml",
            action="store_true",
            help="Enable Machine Learning E.g. seasonal ARIMA model for predictions",
        )
        parser.add_argument(
            "--enable_pandas_ta", action="store_true", help="Enable Pandas-ta"
        )
        parser.add_argument(
            "--enable_custom_strategy",
            action="store_true",
            help="EnableCustom Strategy",
        )
        parser.add_argument("--websocket", action="store_true", help="Enable websocket")
        parser.add_argument(
            "--logbuysellinjson",
            action="store_true",
            help="Enable logging orders in json format",
        )
        parser.add_argument(
            "--startmethod", type=str, help="Enable logging orders in json format"
        )
        parser.add_argument(
            "--manual_trades_only",
            action="store_true",
            help="Manual Trades Only (HODL)",
        )

        # TODO: arguments v2

        parser.add_argument(
            "--preventloss",
            type=int,
            help="Sell before margin is negative",
        )
        parser.add_argument(
            "--preventlosstrigger",
            type=float,
            help="Margin that will trigger the prevent loss",
        )
        parser.add_argument(
            "--preventlossmargin",
            type=float,
            help="Margin that will cause an immediate sell to prevent loss",
        )
        parser.add_argument(
            "--sellatloss", type=int, help="Allow a sell if the profit margin is negative"
        )

        parser.add_argument(
            "--bullonly",
            type=int,
            help="Only trade in a bull market SMA50 > SMA200",
        )

        parser.add_argument(
            "--sellatresistance",
            type=int,
            help="Sell if the price hits a resistance level",
        )
        parser.add_argument(
            "--sellatfibonaccilow",
            type=int,
            help="Sell if the price hits a fibonacci lower level",
        )
        parser.add_argument(
            "--profitbankreversal",
            type=int,
            help="Sell at candlestick strong reversal pattern",
        )

        parser.add_argument(
            "--trailingstoploss",
            type=float,
            help="Percentage below the trade margin high to sell",
        )
        parser.add_argument(
            "--trailingstoplosstrigger",
            type=float,
            help="Trade margin percentage to enable the trailing stop loss",
        )
        parser.add_argument(
            "--trailingsellpcnt",
            type=float,
            help="Percentage of decrease to wait before selling",
        )
        parser.add_argument(
            "--trailingimmediatesell",
            action="store_true",
            help="Immediate sell if trailing sell percent is reached",
        )
        parser.add_argument(
            "--trailingsellimmediatepcnt",
            type=float,
            help="Percentage of decrease used with a strong sell signal",
        )
        parser.add_argument(
            "--trailingsellbailoutpcnt",
            type=float,
            help="Percentage of decrease to bailout, sell immediately",
        )

        parser.add_argument(
            "--dynamictsl",
            type=int,
            help="Dynamic Trailing Stop Loss (TSL)",
        )
        parser.add_argument(
            "--tslmultiplier",
            type=float,
            help="TSL Multiplier",
        )
        parser.add_argument(
            "--tsltriggermultiplier",
            type=float,
            help="TSL Trigger Multiplier",
        )
        parser.add_argument(
            "--tslmaxpcnt",
            type=float,
            help="TSL Max Percent",
        )

        parser.add_argument(
            "--buynearhigh",
            type=int,
            help="Prevent the bot from buying at a recent high",
        )
        parser.add_argument(
            "--buynearhighpcnt",
            type=float,
            help="Percentage from the range high to not buy",
        )
        parser.add_argument(
            "--adjusttotalperiods",
            type=int,
            help="Adjust data points in historical trading data",
        )

        parser.add_argument(
            "--selltriggeroverride <0|1>",
            action="store_true",
            help="Override sell trigger if strong buy",
        )

        parser.add_argument(
            "--ema1226", type=int, help="Enable EMA12/EMA26 crossovers"
        )
        parser.add_argument(
            "--macdsignal", type=int, help="Enable MACD/Signal crossovers"
        )
        parser.add_argument(
            "--obv", type=int, help="Enable On-Balance Volume (OBV)"
        )
        parser.add_argument(
            "--elderray", type=int, help="Enable Elder-Ray Indices"
        )

        # pylint: disable=unused-variable
        args, unknown = parser.parse_known_args()
        return vars(args)
