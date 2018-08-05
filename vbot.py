from retrying import retry
from botdb import BotDB
from config import Config
from mwt import MWT
import telepot
import time
import sys


class Bot:
    config = None
    botDB = None
    bot = None
    admins = []

    def __init__(self, cfg, db):
        self.config = cfg
        self.botDB = db

    def start(self):
        try:
            self.bot = telepot.Bot(self.config.get('telegram', 'bot_token'))
            self.bot.setWebhook('')  # Remove existent webhook
            self.bot.message_loop(
                self.handle_message,
                relax=self.config.getint('telegram', 'polling_interval'))
        except telepot.exception.TelegramError:
            print("ERROR: Couldn't start Telegram bot. Check telegram bot configuration.")
            sys.exit()

    @MWT(timeout=60 * 60)
    def get_botadmins(self):
        #  Returns a list of bot admins. Results are cached for 1 hour.
        return [item[0] for item in self.botDB.callproc('usp_getadmins')]  # convert first column to list

    def get_message_report(self, username, days=1):
        data = self.botDB.callproc('usp_getmessagereport', [username, days])
        # Adding headers
        if len(data[0]) < 4:  # report invoked by regular admin
            return [("DATE", "GROUP", "MESSAGES")] + data
        else:  # report invoked by root admin
            return [("USERNAME", "GROUP", "DATE", "MESSAGES")] + data

    def save_messages(self, username, date, message, group):
        fdate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(date))  # format epoch
        self.botDB.callproc('usp_savemessages', [username, fdate, message, group])

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_delay=60000)
    def handle_message(self, msg):
        if 'username' not in msg['from'] or msg['from']['username'] not in self.get_botadmins():
            return None  # Ignore non admin users

        if 'text' in msg:
            self.parse_message(msg)

    def reply(self, msg, reply):
        self.bot.sendMessage(msg['chat']['id'], reply, parse_mode='Markdown')

    def parse_message(self, msg):
        command = msg["text"].strip().split(' ')
        csv_file = "report.csv"

        print(msg["chat"]["id"])
        if command[0] == '/getreport' and len(command) == 1:
            cs_writer(self.get_message_report(msg["from"]["username"]), csv_file)
            self.bot.sendDocument(msg["chat"]["id"], open(csv_file, 'rb'))  # send report

        elif command[0] == '/getreport' and len(command) == 2:
            if command[1].isdigit():
                days = command[1]
                cs_writer(self.get_message_report(msg["from"]["username"], days), csv_file)
                self.bot.sendDocument(msg["chat"]["id"], open(csv_file, 'rb'))  # send report

        elif command[0] == '/start':  # Show commands help, also works for /start command
            help_text = (
                "*VBot community voting bot*\n"
                "Available commands:\n\n"
                "/start\n"
                "Show this help\n\n"
                "/getreport\n"
                "Generate message report. Default is 1 day, /getreport 2 will get 2 days i.e\n\n"
                )
            self.reply(msg, help_text)
        else:  # No report needed, just save the message
            self.save_messages(msg["from"]["username"], msg["date"], msg["text"], msg["chat"]["title"])


if __name__ == '__main__':
    config = Config()
    bot = Bot(config.get(), BotDB(config.get()))
    bot.start()

    while True:
        time.sleep(10)
