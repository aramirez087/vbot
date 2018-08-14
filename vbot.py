import logging

from retrying import retry
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from botdb import BotDB
from config import Config
from mwt import MWT


class Bot:
    updater = None
    config = None
    logger = None
    botDB = None
    dp = None
    admins = []

    def __init__(self, cfg, db):
        self.config = cfg
        self.botDB = db
        self.admins = self.get_botadmins()

    def start(self):
        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Setup bot
        self.updater = Updater(self.config.get('telegram', 'bot_token'))
        self.dp = self.updater.dispatcher
        # Add commands
        self.dp.add_handler(CommandHandler(['start', 'help'], self.help))
        self.dp.add_handler(CommandHandler('getreport', self.get_report, pass_args=True, filters=Filters.user(self.admins)))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.private & Filters.user(self.admins), self.save_message))
        self.dp.add_error_handler(self.error)
        self.updater.start_polling()  # Start the Bot
        self.logger.info('Listening...')
        self.updater.idle()  # Run the bot until you press Ctrl-C or the process receives SIGINT

    def help(self, bot, update):
        update.message.reply_text("*VBot community voting bot*\n"
                                  "Available commands:\n\n"
                                  "/start\n"
                                  "Show this help\n\n"
                                  "/getreport\n"
                                  "Generate message report. Default is 1 day, /getreport 2 will get 2 days i.e\n\n")

    def error(self, bot, update, error):
        """Log all errors"""
        self.logger.warning(f'Update "{update}" caused error "{error}"')

    @MWT(timeout=60 * 30)
    def get_botadmins(self):
        """Returns a list of bot admins. Results are cached for 30 minutes"""
        return [item[0] for item in self.botDB.callproc('usp_getadmins')]  # convert first column to list

    def get_message_report(self, userid, days):
        return self.botDB.callproc('usp_getmessagereport', [userid, days], addheaders=True)

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_delay=60000)
    def get_report(self, bot, update, args=None):
        csv_file = "report.csv"
        days = "1" if args is None else args[0]  # default to 1 if not supplied

        if not days.isdigit() or (int(days) < 0 or int(days) > 365):
            update.message.reply_text("Please provide a numeric value between 0 and 365")
            return None  # command args validation

        self.botDB.savecsv(self.get_message_report(update.message.from_user.id, days), csv_file)
        with open(csv_file, 'rb') as f:
            bot.sendDocument(update.message.chat.id, f)  # send report

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_delay=60000)
    def save_message(self, bot, update):
        m = update.message
        self.botDB.callproc('usp_savemessages', [m.from_user.id, m.from_user.username, m.chat.id, m.chat.title, m.date, m.text])


def main():
    config = Config()
    bot = Bot(config.get(), BotDB(config.get()))
    bot.start()


if __name__ == '__main__':
    main()
