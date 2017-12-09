import imaplib
import email
import datetime
import os
import sys
import argparse
import logging

from pymongo import MongoClient

from wheatonslack.bot import Bot
from wheatonslack.imap import Inbox

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--prime', 
        help='Prime db with existing messages',
        action='store_true',
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
    )

    mongo = MongoClient(os.environ.get('MONGO_DB_URI'))
    bot = Bot(None)
    inbox = Inbox(
        os.environ.get('SENDER_USER'), 
        os.environ.get('SENDER_PASS'),
        mongo['slack'],
        bot,
    )

    inbox.post = inbox.post_unthreaded

    if args.prime:
        date = datetime.date.today() - datetime.timedelta(days=365)
        inbox.run(date)
        sys.exit(0)


    date = datetime.date.today() - datetime.timedelta(days=3)
    inbox.run(date)
    #inbox.process_uid(120)
    #inbox.process_uid(140)

    """
    bot.slack_client.rtm_connect()
    while True:
        inbox.run(bot)

        slack_out = bot.slack_client.rtm_read()
        bot.parse_slack_output(slack_out)

        time.sleep(1)
    """


if __name__ == '__main__':
    main()
