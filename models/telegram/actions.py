import os
import json
import subprocess
import logging
import csv
from datetime import datetime

from time import sleep
from models.telegram.helper import TelegramHelper

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

class TelegramActions():
    def __init__(self, datafolder, tg_helper: TelegramHelper) -> None:
        self.datafolder = datafolder

        self.helper = tg_helper

    def _getMarginText(self, market):
        light_icon, margin_icon = ("\U0001F7E2" if "-" not in self.helper.data["margin"] else "\U0001F534", "\U0001F973" if "-" not in self.helper.data["margin"] else "\U0001F97A")

        result = f"{light_icon} <b>{market}</b>\n" \
                    f"{margin_icon} Margin: {self.helper.data['margin']}  " \
                    f"\U0001F4B0 P/L: {self.helper.data['delta']}\n" \
                    f"TSL Trg: {self.helper.data['trailingstoplosstriggered']}  " \
                    f"TSL Change: {float(self.helper.data['change_pcnt_high']).__round__(4)}\n"
        return result

    def _getUptime(self, date: str):
        now = str(datetime.now())
        # If date passed from datetime.now() remove milliseconds
        if date.find(".") != -1:
            dt = date.split(".")[0]
            date = dt
        if now.find(".") != -1:
            dt = now.split(".", maxsplit=1)[0]
            now = dt

        now = now.replace("T", " ")
        now = f"{now}"
        # Add time in case only a date is passed in
        # new_date_str = f"{date} 00:00:00" if len(date) == 10 else date
        date = date.replace("T", " ") if date.find("T") != -1 else date
        # Add time in case only a date is passed in
        new_date_str = f"{date} 00:00:00" if len(date) == 10 else date

        started = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        duration = now - started
        duration_in_s = duration.total_seconds()
        hours = divmod(duration_in_s, 3600)[0]
        duration_in_s -= 3600 * hours
        minutes = divmod(duration_in_s, 60)[0]
        return f"{round(hours)}h {round(minutes)}m"

    def startOpenOrders(self, update):
        logger.info("called startOpenOrders")
        query = update.callback_query
        if query != None:
            query.answer()
            self.helper.sendtelegramMsg(update,
                "<b>Starting markets with open trades..</b>")
        else:
            self.helper.sendtelegramMsg(update, "<b>Starting markets with open trades..</b>")
            # update.effective_message.reply_html("<b>Starting markets with open trades..</b>")

        self.helper.read_data()
        for market in self.helper.data["opentrades"]:
            if not self.helper.isBotRunning(market):
                # update.effective_message.reply_html(f"<i>Starting {market} crypto bot</i>")
                self.helper.startProcess(market, self.helper.data["opentrades"][market]["exchange"], "", "scanner")
            sleep(10)
        self.helper.sendtelegramMsg(update, "<i>Markets have been started</i>")
        # update.effective_message.reply_html("<i>Markets have been started</i>")
        sleep(1)
        self.getBotInfo(update)

    def sellresponse(self, update):
        """create the manual sell order"""
        query = update.callback_query
        logger.info("called sellresponse - %s", query.data)

        if query.data.__contains__("all"):
            self.helper.sendtelegramMsg(update, "<b><i>Initiating sell orders..</i></b>")
            for market in self.helper.getActiveBotList("active"):
                while self.helper.read_data(market) is False:
                    sleep(0.2)

                if "margin" in self.helper.data and self.helper.data["margin"] != " ":
                    while self.helper.read_data(market) is False:
                        sleep(0.2)

                    if "botcontrol" in self.helper.data:
                        self.helper.data["botcontrol"]["manualsell"] = True
                        self.helper.write_data(market)
                        self.helper.sendtelegramMsg(update,
                            f"Selling: {market}\n<i>Please wait for sale notification...</i>")
                sleep(0.2)
        else:
            while self.helper.read_data(query.data.replace("confirm_sell_", "")) is False:
                sleep(0.2)
            if "botcontrol" in self.helper.data:
                self.helper.data["botcontrol"]["manualsell"] = True
                self.helper.write_data(query.data.replace("confirm_sell_", ""))
                self.helper.sendtelegramMsg(update,
                    f"Selling: {query.data.replace('confirm_sell_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
                )

    def buyresponse(self, update):
        """create the manual buy order"""
        query = update.callback_query
        logger.info("called buyresponse - %s", query.data)
        # if self.helper.read_data(query.data.replace("confirm_buy_", "")):
        while self.helper.read_data(query.data.replace("confirm_buy_", "")) is False:
            sleep(0.2)
        if "botcontrol" in self.helper.data:
            self.helper.data["botcontrol"]["manualbuy"] = True
            self.helper.write_data(query.data.replace("confirm_buy_", ""))
            self.helper.sendtelegramMsg(update,
                f"Buying: {query.data.replace('confirm_buy_', '').replace('.json','')}\n<i>Please wait for sale notification...</i>",
            )

    def showconfigresponse(self, update):
        """display config settings based on exchanged selected"""
        self.helper.read_config()
        # with open(os.path.join(self.helper.config_file), "r", encoding="utf8") as json_file:
        #     self.helper.config = json.load(json_file)

        query = update.callback_query
        logger.info("called showconfigresponse - %s", query.data)

        if query.data == "ex_scanner":
            pbot = self.helper.config[query.data.replace("ex_", "")]
        else:
            pbot = self.helper.config[query.data.replace("ex_", "")]["config"]

        self.helper.sendtelegramMsg(update, query.data.replace("ex_", "") + "\n" + json.dumps(pbot, indent=4))

    def getBotInfo(self, update):

        count = 0
        for file in self.helper.getActiveBotList():
            output = ""
            count += 1
            
            while self.helper.read_data(file) == False:
                sleep(0.2)

            output = output + f"\U0001F4C8 <b>{file}</b> "

            last_modified = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(
                    os.path.join(self.datafolder, "telegram_data", f"{file}.json")
                )
            )

            icon = "\U0001F6D1" # red dot
            if last_modified.seconds > 90 and last_modified.seconds != 86399:
                output = f"{output} {icon} <b>Status</b>: <i>defaulted</i>"
            elif "botcontrol" in self.helper.data and "status" in self.helper.data["botcontrol"]:
                if self.helper.data["botcontrol"]["status"] == "active":
                    icon = "\U00002705" # green tick
                if self.helper.data["botcontrol"]["status"] == "paused":
                    icon = "\U000023F8" # pause icon
                if self.helper.data["botcontrol"]["status"] == "exit":
                    icon = "\U0000274C" # stop icon
                output = f"{output} {icon} <b>Status</b>: <i>{self.helper.data['botcontrol']['status']}</i>"
                output = f"{output} \u23F1 <b>Uptime</b>: <i>{self._getUptime(self.helper.data['botcontrol']['started'])}</i>\n"
            else:
                output = f"{output} {icon} <b>Status</b>: <i>stopped</i> "

            if count == 1:
                self.helper.sendtelegramMsg(update, output)
            else:
                update.effective_message.reply_html(f"{output}")
            sleep(0.2)

        if count == 0:
            self.helper.sendtelegramMsg(update, f"<b>Bot Count ({count})</b>")
        else:
            update.effective_message.reply_html(f"<b>Bot Count ({count})</b>")

    def getMargins(self, update):
        query = update.callback_query

        self.helper.sendtelegramMsg(update, "<i>Getting Margins..</i>")
        cOutput = []
        oOutput = []
        closedbotCount = 0
        openbotCount = 0
        # print(self.helper.getActiveBotList())
        for market in self.helper.getActiveBotList():
            while self.helper.read_data(market) is False:
                sleep(0.2)

            closedoutput = "" 
            openoutput = ""
            if "margin" in self.helper.data:
                if "margin" in self.helper.data and self.helper.data["margin"] == " ":
                    closedoutput = (closedoutput + f"<b>{market}</b>")
                    closedoutput = closedoutput + f"\n<i>{self.helper.data['message']}</i>\n"
                    cOutput.append(closedoutput)
                    closedbotCount += 1
                elif len(self.helper.data) > 2:
                    openoutput = openoutput + self._getMarginText(market)
                    oOutput.append(openoutput)
                    openbotCount += 1

        if (query.data.__contains__("orders") or query.data.__contains__("all")) and openbotCount > 0:
            for output in oOutput:
                update.effective_message.reply_html(f"{output}")
                sleep(0.5)

        elif (query.data.__contains__("orders") or query.data.__contains__("all")) and openbotCount == 0:
            update.effective_message.reply_html("<b>No open orders found.</b>")

        if (query.data.__contains__("pairs") or query.data.__contains__("all")) and closedbotCount > 0:
            for output in cOutput:
                update.effective_message.reply_html(f"{output}")
                sleep(1)

        elif (query.data.__contains__("pairs") or query.data.__contains__("all")) and closedbotCount == 0:
            update.effective_message.reply_html("<b>No active pairs found.</b>")

    def StartMarketScan(self, update, use_default_scanner: bool = True, scanmarkets: bool = True, startbots: bool = True, debug: bool = False):

        #Check whether using the scanner or the screener - use correct config file etc
        if use_default_scanner == True:
            scanner_config_file = "scanner.json"
            scanner_script_file = "scanner.py"
        elif use_default_scanner == False:
            scanner_config_file = "screener.json"
            scanner_script_file = "screener.py"
        
        logger.info("called StartMarketScan - %s", scanner_script_file)

        try:
            with open(f"{scanner_config_file}", encoding="utf8") as json_file:
                config = json.load(json_file)
        except IOError as err:
            self.helper.sendtelegramMsg(update,
                f"<i>{scanner_config_file} config error</i>\n{err}"
            )
            return

        # If a bulk load file for the exchange exists - start up all the bulk bots for this 

        for ex in config:
            for quote in config[ex]["quote_currency"]:
                if os.path.exists(os.path.join(self.datafolder, "telegram_data", f"{ex}_bulkstart.csv")):
                    update.effective_message.reply_html(f"<i>Found bulk load CSV file for {ex}... Loading pairs</i>")
                    try:
                        with open(os.path.join(self.datafolder, "telegram_data", f"{ex}_bulkstart.csv"), newline='', encoding='utf-8') as csv_obj:
                            csv_file = csv.DictReader(csv_obj)
                            for row in csv_file:
                                #update.effective_message.reply_html(row["market"])
                                if "market" in row and row["market"] != None and quote in row["market"]:
                                    # Start the process disregarding bot limits for the moment
                                    update.effective_message.reply_html(f"Bulk Starting {row['market']} on {ex}...")
                                    self.helper.startProcess(row["market"], ex, "", "scanner")
                                    sleep(7)
                    except IOError as err:
                        pass
                else:
                #No Bulk Start File Found
                    pass

        if scanmarkets:
            reply = "<i>Gathering market data\nplease wait...</i> \u23F3"
            self.helper.sendtelegramMsg(update, reply)
            try:
                logger.info("Starting Market Scanner")
                subprocess.getoutput(f"python3 {scanner_script_file}")
            except Exception as err:
                update.effective_message.reply_html("<b>scanning failed.</b>")
                logger.error(err)
                raise

            update.effective_message.reply_html("<b>Scan Complete.</b>")

        # Watchdog process - check for hung bots and force restart them

        update.effective_message.reply_html("<i>Fido checking for hung bots..</i>")
        for file in self.helper.getHungBotList():
            ex = self.helper.getRunningBotExchange(file)
            self.helper.stopRunningBot(file, "exit", True)
            sleep(3)
            os.remove(os.path.join(self.datafolder, "telegram_data", f"{file}.json"))
            #self.helper._cleandataquietall()
            sleep(1)
            update.effective_message.reply_html(f"Restarting {file} as it appears to have hung...")
            self.helper.startProcess(file, ex, "", "scanner")
            sleep(1)

        if not startbots:
            update.effective_message.reply_html("<b>Operation Complete (0 started)</b>")
            return

        # Check to see if the bot would be restarted anyways from the scanner - and dont stop to maintain trailingbuypcnt etc

        scanned_bots = []

        for ex in config:
            for quote in config[ex]["quote_currency"]:
                try:
                    with open(
                        os.path.join(
                            self.datafolder, "telegram_data", f"{ex}_{quote}_output.json"
                            ), "r", encoding="utf8") as json_file:
                        data = json.load(json_file)
                    for row in data:
                        if data[row]["atr72_pcnt"] != None:
                            if data[row]["atr72_pcnt"] >= self.helper.config["scanner"]["atr72_pcnt"]:
                                scanned_bots.append(row)
                except:
                    pass

        update.effective_message.reply_html("<i>stopping bots..</i>")
        active_bots_list = self.helper.getActiveBotList()
        open_order_bot_list = self.helper.getActiveBotListWithOpenOrders()
        for file in active_bots_list:
            if (file not in scanned_bots) or (file not in open_order_bot_list):
                self.helper.stopRunningBot(file, "exit")
                sleep(3)
            else:
                update.effective_message.reply_html(f"Not stopping {file} - in scanner list, or has open order...")

        botcounter = 0
        runningcounter = len(self.helper.getActiveBotList())
        maxbotcount = self.helper.config["scanner"]["maxbotcount"] if "maxbotcount" in self.helper.config["scanner"] else 0

        self.helper.read_data()
        for ex in config:
            if maxbotcount > 0 and botcounter >= maxbotcount:
                break
            for quote in config[ex]["quote_currency"]:
                update.effective_message.reply_html(f"Starting {ex} ({quote}) bots...")
                logger.info("%s - (%s)", ex, quote)
                if not os.path.isfile(os.path.join(self.datafolder, "telegram_data", f"{ex}_{quote}_output.json")):
                    continue

                with open(
                    os.path.join(
                        self.datafolder, "telegram_data", f"{ex}_{quote}_output.json"
                        ), "r", encoding="utf8") as json_file:
                    data = json.load(json_file)

                outputmsg =  f"<b>{ex} ({quote})</b> \u23F3 \n"

                msg_cnt = 1
                for row in data:
                    if debug:
                        logger.info("%s", row)

                    if self.helper.config["scanner"]["maxbotcount"] > 0 and botcounter >= self.helper.config["scanner"]["maxbotcount"]:
                        break
                    
                    if self.helper.config["scanner"]["enableleverage"] == False \
                            and (str(row).__contains__(f"DOWN{quote}") or str(row).__contains__(f"UP{quote}") or str(row).__contains__(f"3L-{quote}") or str(row).__contains__(f"3S-{quote}")):
                        if msg_cnt == 1:
                            update.effective_message.reply_html(f"Ignoring {ex} ({quote}) Leverage Pairs (enableleverage is disabled)...")    
                            msg_cnt += 1
                        continue

                    if row in self.helper.data["scannerexceptions"]:
                        outputmsg = outputmsg + f"*** {row} found on scanner exception list ***\n"
                    else:
                        if data[row]["atr72_pcnt"] != None:
                            if data[row]["atr72_pcnt"] >= self.helper.config["scanner"]["atr72_pcnt"]:
                                if self.helper.config["scanner"]["enable_buy_next"] and data[row]["buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%  //--//  <b>buy_next:</b> {data[row]['buy_next']}</i>\n"
                                    self.helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                elif not self.helper.config["scanner"]["enable_buy_next"]:
                                    outputmsg = outputmsg + f"<i><b>{row}</b>  //--//  <b>atr72_pcnt:</b> {data[row]['atr72_pcnt']}%</i>\n"
                                    self.helper.startProcess(row, ex, "", "scanner")
                                    botcounter += 1
                                if debug == False:
                                    sleep(6)

                update.effective_message.reply_html(f"{outputmsg}")

        update.effective_message.reply_html(f"<i>Operation Complete.  ({botcounter-runningcounter} started)</i>")

    def deleteresponse(self, update):
        """delete selected bot"""
        self.helper.read_data()

        query = update.callback_query
        logger.info("called deleteresponse - %s", query.data)
        self.helper.data["markets"].pop(str(query.data).replace("delete_", ""))

        self.helper.write_data()

        self.helper.sendtelegramMsg(update,
            f"<i>Deleted {str(query.data).replace('delete_', '')} crypto bot</i>"
        )

    def RemoveExceptionCallBack(self, update):
        """delete selected bot"""
        self.helper.read_data()

        query = update.callback_query
 
        self.helper.data["scannerexceptions"].pop(str(query.data).replace("delexcep_", ""))

        self.helper.write_data()

        self.helper.sendtelegramMsg(update,
            f"<i>Removed {str(query.data).replace('delexcep_', '')} from exception list. bot</i>"
        )