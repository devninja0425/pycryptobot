""" Telegram Bot Helper """
import os
import platform
import subprocess
import json
import logging
# from time import sleep
from json.decoder import JSONDecodeError
# from time import sleep
from datetime import datetime
from typing import List
from telegram import InlineKeyboardMarkup, Update
from telegram.ext.callbackcontext import CallbackContext

if not os.path.exists(os.path.join(os.curdir, "telegram_logs")):
    os.mkdir(os.path.join(os.curdir, "telegram_logs"))

logging.basicConfig(
    filename=os.path.join(os.curdir, "telegram_logs", f"telegrambot {datetime.now().strftime('%Y-%m-%d')}.log"),
    filemode='w',
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
)

# logger = logging.getLogger(__name__)

class TelegramHelper:
    """ Telegram Bot Helper """
    def __init__(self, datafolder, config, configfile) -> None:
        self.datafolder = datafolder
        self.data = {}
        self.config = config
        self.config_file = configfile
        self.screener = {}
        self.settings = {}
        self.use_default_scanner = True
        self.atr72pcnt = 2.0
        self.enableleverage = False
        self.maxbotcount = 0
        self.exchange_bot_count = 0
        self.autoscandelay = 0
        self.enable_buy_next = True
        self.autostart = False
        self.logger_level = "INFO"

        self.logger = logging.getLogger("telegram.helper")
        self.logger.setLevel(self.get_level(self.logger_level))
        self.terminal_start_process = ""

        self.load_config()
        self.read_screener_config()

        self.logger.setLevel(self.get_level(self.logger_level))
        # set a format which is simpler for console use
        consoleHandlerFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # define a Handler which writes sys.stdout
        consoleHandler = logging.StreamHandler()
        # Set log level
        consoleHandler.setLevel(self.get_level(self.logger_level))
        # tell the handler to use this format
        consoleHandler.setFormatter(consoleHandlerFormatter)
        # add the handler to the root logger
        self.logger.addHandler(consoleHandler)

    @classmethod
    def get_level(cls, level):
        if level == "CRITICAL":
            return logging.CRITICAL
        elif level == "ERROR":
            return logging.ERROR
        elif level == "WARNING":
            return logging.WARNING
        elif level == "INFO":
            return logging.INFO
        elif level == "DEBUG":
            return logging.DEBUG
        else:
            return logging.NOTSET

    def load_config(self):
        ''' Load/Reread config file from file '''
        self.read_config()

        if "scanner" in self.config:
            self.atr72pcnt = (
                self.config["scanner"]["atr72_pcnt"]
                if "atr72_pcnt" in self.config["scanner"]
                else self.atr72pcnt
            )
            self.enableleverage = (
                bool(self.config["scanner"]["enableleverage"])
                if "enableleverage" in self.config["scanner"]
                else self.enableleverage
            )
            self.use_default_scanner = (
                bool(self.config["scanner"]["use_default_scanner"])
                if "use_default_scanner" in self.config["scanner"]
                else self.use_default_scanner
            )
            self.maxbotcount = (
                self.config["scanner"]["maxbotcount"]
                if "maxbotcount" in self.config["scanner"]
                else self.maxbotcount
            )
            self.exchange_bot_count = (
                self.config["scanner"]["exchange_bot_count"]
                if "exchange_bot_count" in self.config["scanner"]
                else self.exchange_bot_count
            )
            self.terminal_start_process = (
                self.config["scanner"]["terminal_start_process"]
                if "terminal_start_process" in self.config["scanner"]
                else self.terminal_start_process
            )
            self.autoscandelay = (
                self.config["scanner"]["autoscandelay"]
                if "autoscandelay" in self.config["scanner"]
                else 0
            )
            self.enable_buy_next = (
                bool(self.config["scanner"]["enable_buy_next"])
                if "enable_buy_next" in self.config["scanner"]
                else True
            )
            # self.logger_level = (
            #     self.config["scanner"]["logger_level"]
            #     if "logger_level" in self.config["scanner"]
            #     else "INFO"
            # )
            self.logger_level = (
                self.config["telegram"]["logger_level"]
                if "logger_level" in self.config["telegram"]
                else "INFO"
            )
    def send_telegram_message(
        self, update: Update , reply, markup: InlineKeyboardMarkup = None, context: CallbackContext = None
    ):
        ''' Send telegram messages '''
        try:
            query = update.callback_query
            query.answer()
        except: # pylint: disable=bare-except
            pass
        try:
            if markup is None:
                query.edit_message_text(reply, parse_mode="HTML")
            else:
                query.edit_message_text(reply, reply_markup=markup, parse_mode="HTML")
        except: # pylint: disable=bare-except
            try:
                context.bot.edit_message_text(chat_id=update.effective_message.chat_id,
                                message_id=update.effective_message.message_id,
                                text=reply,
                                reply_markup=markup,
                                parse_mode="HTML"
                                )
            except: # pylint: disable=bare-except
                context.bot.send_message(chat_id=update.effective_message.chat_id,
                                text=reply,
                                reply_markup=markup,
                                parse_mode="HTML")

    def read_data(self, name: str = "data.json") -> bool:
        ''' Read data from json file '''
        fname = name if name.__contains__(".json") else f"{name}.json"
        # self.logger.debug("METHOD(read_data) - DATA(%s)", fname)
        read_ok, try_count = False, 0
        while not read_ok and try_count <= 20:
            try_count += 1
            try:
                self.data = {}
                with open(
                    os.path.join(self.datafolder, "telegram_data", fname),
                    "r",
                    encoding="utf8",
                ) as json_file:
                    self.data = json.load(json_file)
                read_ok = True
            except FileNotFoundError:
                if try_count == 20:
                    self.logger.error("File Not Found {%s}", fname)
                # else:
                    # sleep(0.2)
            except JSONDecodeError:
                if try_count == 20:
                    self.logger.error("Unable to read file {%s}", fname)
                # else:
                    # sleep(0.2)
            
        return read_ok

    def write_data(self, name: str = "data.json") -> None:
        ''' Write data to json file '''
        fname = name if name.__contains__(".json") else f"{name}.json"
        self.logger.debug("METHOD(write_data) - DATA(%s)", fname)
        try:
            with open(
                os.path.join(self.datafolder, "telegram_data", fname),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.data, outfile, indent=4)
                return True
        except JSONDecodeError as err:
            self.logger.error(err)
            return False

    def read_config(self):
        ''' Read config file '''
        self.logger.debug("METHOD(read_config)")
        try:
            with open(
                os.path.join(self.config_file), "r", encoding="utf8"
            ) as json_file:
                self.config = json.load(json_file)
        except FileNotFoundError:
            return
        except json.decoder.JSONDecodeError:
            return

    def write_config(self):
        ''' Write config file '''
        self.logger.debug("METHOD(write_config)")
        try:
            with open(
                os.path.join(self.config_file),
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.config, outfile, indent=4)
        except: # pylint: disable=bare-except
            return

    def read_screener_config(self):
        ''' Read screener config file '''
        self.logger.debug("METHOD(read_screener_config)")
        try:
            with open(
                "screener.json", "r", encoding="utf8"
            ) as json_file:
                self.screener = json.load(json_file)
        except FileNotFoundError:
            return
        except json.decoder.JSONDecodeError:
            return

    def write_screener_config(self):
        ''' Write screener config file '''
        self.logger.debug("METHOD(write_screener_config)")
        try:
            with open(
                "screener.json",
                "w",
                encoding="utf8",
            ) as outfile:
                json.dump(self.screener, outfile, indent=4)
        except: # pylint: disable=bare-except
            return

    def get_all_bot_list(self) -> List[str]:
        """Return ALL contents of telegram_data folder"""
        self.logger.debug("METHOD(get_all_bot_list)")
        jsonfiles = sorted(os.listdir(os.path.join(self.datafolder, "telegram_data")))

        i = len(jsonfiles) - 1
        while i >= 0:
            if (
                jsonfiles[i] == "data.json"
                or jsonfiles[i].__contains__("output.json")
                or jsonfiles[i].__contains__(".csv")
                or jsonfiles[i] == "settings.json"
            ):
                jsonfiles.pop(i)
            else:
                read_ok = self.read_data(jsonfiles[i])
                if not read_ok:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_active_bot_list(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder"""
        self.logger.debug("METHOD(get_active_bot_list) - DATA(%s)", state)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if not self.data["botcontrol"]["status"] == state:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_active_bot_list_with_open_orders(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder active bots with an open order"""
        self.logger.debug("METHOD(get_active_bot_list_with_open_orders) - DATA(%s)", state)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if self.data["margin"] == " ":
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_hung_bot_list(self, state: str = "active") -> List[str]:
        """Return contents of telegram_data folder - working out which are hung bots"""
        self.logger.debug("METHOD(get_hung_bot_list) - DATA(%s)", state)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            elif "botcontrol" in self.data:
                if "watchdog_ping" in self.data["botcontrol"]:
                    last_ping = datetime.strptime(self.data["botcontrol"]["watchdog_ping"], "%Y-%m-%dT%H:%M:%S.%f")
                    current_dt = datetime.now()
                    ping_delta = int((current_dt - last_ping).total_seconds())
                    if (self.data["botcontrol"]["status"] == state and ping_delta < 600):
                        jsonfiles.pop(i)
                else:
                    start_time = datetime.strptime(self.data["botcontrol"]["started"], "%Y-%m-%dT%H:%M:%S.%f")
                    current_dt = datetime.now()
                    start_delta = int((current_dt - start_time).total_seconds())
                    if (self.data["botcontrol"]["status"] == state and start_delta < 300):
                        jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def get_manual_started_bot_list(self, startMethod: str = "telegram") -> List[str]:
        """Return contents of telegram_data folder"""
        self.logger.debug("METHOD(get_manual_started_bot_list) - DATA(%s)", startMethod)
        jsonfiles = self.get_all_bot_list()

        i = len(jsonfiles) - 1
        while i >= 0:
            read_ok = self.read_data(jsonfiles[i])
            if not read_ok:
                jsonfiles.pop(i)
                i -= 1
                continue
            if "botcontrol" in self.data:
                if not self.data["botcontrol"]["startmethod"] == startMethod:
                    jsonfiles.pop(i)
            i -= 1
        jsonfiles.sort()
        return [
            x.replace(".json", "") if x.__contains__(".json") else x for x in jsonfiles
        ]

    def is_bot_running(self, pair) -> bool:
        ''' Check is bot running (pair.json file exists)'''
        self.logger.debug("METHOD(is_bot_running) - DATA(%s)", pair)
        if os.path.isfile(
            os.path.join(self.datafolder, "telegram_data", f"{pair}.json")
        ):
            return True

        return False

    def get_running_bot_exchange(self, pair) -> str:
        ''' Get bots exchange '''
        self.logger.debug("METHOD(get_running_bot_exchange) - DATA(%s)", pair)
        if self.read_data(f"{pair}.json") is True:
            return self.data["exchange"]
        return "None"

    def start_process(
        self,
        pair,
        exchange,
        overrides,
        startmethod: str = "telegram",
        return_output: bool = False,
    ):
        """Start a new subprocess"""
        self.logger.debug("METHOD(start_process) - DATA(%s, %s, %s, %s)", pair, exchange, overrides,startmethod)
        if self.is_bot_running(pair):
            return False

        if return_output is True:
            return subprocess.getoutput(
                f"python3 pycryptobot.py --exchange {exchange} --market {pair} {overrides}"
            )

        command = "python3 pycryptobot.py"
        command = f"{command} --startmethod {startmethod}"

        if pair != "":
            command = f"{command} --market {pair}"
        if exchange != "":
            command = f"{command} --exchange {exchange}"

        if platform.system() == "Windows":
            os.system(
                f"start powershell -Command $host.UI.RawUI.WindowTitle = '{pair}' ; "
                f"{command} --logfile './logs/{exchange}-{pair}-{datetime.now().date()}.log' "\
                    f"{overrides}"
            )
        else:
            if self.terminal_start_process != "":
                command = f"{self.terminal_start_process} {command}"
            subprocess.Popen(
                f"{command} --logfile './logs/{exchange}-{pair}-{datetime.now().date()}.log' "\
                    f"{overrides}",
                shell=True,
            )

        return True

    def update_bot_control(self, pair, status) -> bool:
        """used to update bot json files for controlling state"""
        self.logger.debug("METHOD(update_bot_control) - DATA(%s, %s)", pair, status)
        read_ok = self.read_data(pair)
        if not read_ok:
            self.logger.warning("update_bot_control for %s unable to read file", pair)
        elif "botcontrol" in self.data:
            self.data["botcontrol"]["status"] = status
            self.write_data(pair)
            return True

        return False

    def stop_running_bot(self, pair, state, is_open: bool = False) -> bool:
        ''' Stop current running bots '''
        self.logger.debug("METHOD(stop_running_bot) - DATA(%s, %s)", pair, state)
        if self.is_bot_running(pair):
            read_ok = self.read_data(pair)
            if not read_ok:
                self.logger.warning("stop_running_bot for %s unable to read file", pair)
            if is_open:
                return self.update_bot_control(pair, state)
            elif "margin" in self.data and self.data["margin"] == " ":
                return self.update_bot_control(pair, state)

    def create_callback_data(self, callback_tag, exchange: str = "", parameter: str = ""):
        return json.dumps({'c':callback_tag,'e': exchange,'p':parameter})