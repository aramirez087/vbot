import logging
import os
import sys

import numpy as np
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from botdb import BotDB
from config import Config
from mwt import MWT


class Bot:
    THUMBS_UP_EMOJI = '\U0001F44D'
    THUMBS_DOWN_EMOJI = '\U0001F44E'
    updater = None
    config = None
    logger = None
    botDB = None
    dp = None
    admins = []
    upvotes = np.array([])
    downvotes = np.array([])

    def __init__(self, cfg):
        self.config = cfg
        self.botDB = BotDB(cfg)
        self.admins = self.get_botadmins()

    def start(self):
        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.WARNING)
        self.logger = logging.getLogger(__name__)
        # Setup bot
        self.updater = Updater(self.config.get('telegram', 'bot_token'))
        self.dp = self.updater.dispatcher
        # Add commands
        self.dp.add_handler(CommandHandler(['start', 'help'], self.help))
        self.dp.add_handler(CommandHandler('getreport',
                                           self.get_report,
                                           pass_args=True,
                                           filters=Filters.user(self.admins)))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.private & Filters.user(self.admins),
                                           self.save_message))
        self.dp.add_handler(CallbackQueryHandler(self.button_pressed))
        # log all errors
        self.dp.add_error_handler(self.error)
        self.updater.start_polling()  # Start the Bot
        self.logger.info('Listening...')
        self.updater.idle()  # Run the bot until you press Ctrl-C or the process receives SIGINT

    def error(self, bot, update, error):
        import traceback
        self.logger.warning('Update "%s" caused error "%s"' % (update, error))
        traceback.print_exc()

    def help(self, bot, update):
        update.message.reply_text("*VBot community voting bot*\n"
                                  "Available commands:\n\n"
                                  "/start\n"
                                  "Show this help\n\n"
                                  "/getreport\n"
                                  "Generate message report. Default is 1 day, /getreport 2 will get 2 days i.e\n\n")

    @MWT(timeout=60 * 30)
    def get_botadmins(self):
        """Returns a list of bot admins. Results are cached for 30 minutes"""
        return [item[0] for item in self.botDB.callproc('usp_getadmins')]  # convert first column to list

    def get_report(self, bot, update, args=None):
        """Send a CSV report with message counts per user/group/day"""
        csv_file = str(update.effective_user.id) + '.csv'
        days = "1" if len(args) == 0 else args[0]  # default to 1 if not supplied
        userid = update.effective_user.id

        if not days.isdigit() or (int(days) < 0 or int(days) > 365):
            update.message.reply_text("Please provide a numeric value between 0 and 365.")
            return None  # command args validation

        self.botDB.savecsv(self.botDB.callproc('usp_getmessagereport', [userid, days], add_headers=True), csv_file)
        if os.stat(csv_file).st_size > 0:
            with open(csv_file, 'rb') as f:
                bot.sendDocument(update.message.chat.id, f)  # send report
        else:
            update.message.reply_text("I didn't find any data.")

    @run_async
    def save_message(self, bot, update):
        if update.message.text.upper().startswith('!FWP'):
            self.create_poll(bot, update)
            return None

        m = update.message
        args = [m.from_user.id, m.from_user.first_name, m.chat.id, m.chat.title, m.date]
        self.botDB.callproc('usp_savemessages', args)

    def label(self, icon, counter=0):
        if counter > 0:
            return '{} {}'.format(icon, counter)
        return icon

    def empty_keyboard(self):
        up_button = self._create_button(self.THUMBS_UP_EMOJI, 1)
        down_button = self._create_button(self.THUMBS_DOWN_EMOJI, 0)
        keyboard = [[up_button, down_button]]
        return InlineKeyboardMarkup(keyboard)

    def keyboard(self):
        up_label = self.label(self.THUMBS_UP_EMOJI, len(self.upvotes))
        down_label = self.label(self.THUMBS_DOWN_EMOJI, len(self.downvotes))
        up_button = self._create_button(up_label, 1)
        down_button = self._create_button(down_label, 0)
        keyboard = [[up_button, down_button]]
        return InlineKeyboardMarkup(keyboard)

    def _create_button(self, label, callback):
        return InlineKeyboardButton(label, callback_data=callback)

    def create_poll(self, bot, update):
        reply_markup = self.empty_keyboard()
        msg = update.message

        title = '<i>Poll created by</i> <a href="tg://user?id=' + str(msg.from_user.id)
        title += '">' + msg.from_user.first_name + '</a> <i>from "' + msg.chat.title + '</i>"\n\n'
        content = msg.text[5:].replace('snet_vbot', '')
        if msg.reply_to_message:
            if msg.reply_to_message.text:
                title += '<b>In response to:\n    "</b>' + \
                         msg.reply_to_message.text + \
                         '"  - <a href="tg://user?id=' + str(msg.reply_to_message.from_user.id)
                title += '">' + msg.reply_to_message.from_user.first_name + '</a>\n\n'
                msgtext = title + '<b>Reply:</b>\n' + content if content != '' else title
                bot.sendMessage(chat_id=self.config.get('telegram', 'vote_channel'),
                                text=msgtext,
                                reply_markup=reply_markup,
                                parse_mode="HTML")
            elif msg.reply_to_message.photo and len(content) <= 150:
                content = ' "' + content + '"' if msg.text else ''
                bot.sendPhoto(chat_id=self.config.get('telegram', 'vote_channel'),
                              photo=msg.reply_to_message.photo[-1],
                              caption='Sent by: ' + msg.from_user.first_name + content,
                              reply_markup=reply_markup
                              )
            elif msg.reply_to_message.photo and len(content) > 150:
                update.message.reply_text("Caption too long, please make it 150 characters max.")
        else:
            if msg.text:
                content = msg.text[5:].replace('snet_vbot', '')
                msgtext = title + '\n' + content if content != '' else title
                bot.sendMessage(chat_id=self.config.get('telegram', 'vote_channel'),
                                text=msgtext,
                                reply_markup=reply_markup,
                                parse_mode="HTML")

    @run_async
    def button_pressed(self, bot, update):
        query = update.callback_query
        m = query.message
        na = np.array(self.botDB.callproc('usp_getvoters', [m.chat_id, m.message_id]))
        self.upvotes = np.array([])
        self.downvotes = np.array([])
        hits = 0

        if na.size > 0:  # avoid working with array when it has no data
            hits = na[(na[:, 0] == update.effective_user.id)][:, 2]  # vote counter
            hits = 0 if len(hits) == 0 else hits[0]
            self.upvotes = na[(na[:, 1] == 1)][:, 0]  # filter numpy array
            self.downvotes = na[(na[:, 1] == 0)][:, 0]

        if query.data and hits < 3:
            prev_vote = "" if hits == 0 else str(na[(na[:, 0] == update.effective_user.id)][:, 1][0])
            vote_args = [m.chat_id, m.message_id, update.effective_user.id, int(query.data)]

            if query.data != prev_vote:  # is previous vote different than this one?
                self.botDB.callproc('usp_savevote', vote_args)
                if query.data == "1":
                    self.up(update.effective_user.id)
                elif query.data == "0":
                    self.down(update.effective_user.id)

                bot.edit_message_reply_markup(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    inline_message_id=query.inline_message_id,
                    reply_markup=self.keyboard()
                )
            else:
                update.callback_query.answer(text='No changes...')
        elif query.data:
            update.callback_query.answer(text='You have already voted, thank you!')

    def up(self, user):
        if len(self.upvotes) > 0 and user in self.upvotes:
            return False

        self.upvotes = np.append(self.upvotes, user)
        if len(self.downvotes) > 0 and user in self.downvotes:
            self.downvotes = np.delete(self.downvotes, np.where(self.downvotes == user))

        return True

    def down(self, user):
        if len(self.downvotes) > 0 and user in self.downvotes:
            return False

        self.downvotes = np.append(self.downvotes, user)
        if len(self.upvotes) > 0 and user in self.upvotes:
            self.upvotes = np.delete(self.upvotes, np.where(self.upvotes == user))

        return True

def main():
    config = Config()
    bot = Bot(config.get())
    bot.start()


if __name__ == '__main__':
    main()
