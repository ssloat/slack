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
    slack = MongoClient(os.environ.get('MONGO_DB_URI'))['slack']

    bot = Bot()
    inbox = Inbox(os.environ.get('SENDER_USER'), os.environ.get('SENDER_PASS'))

    delta = 365 if args.prime else 3
    date = datetime.date.today() - datetime.timedelta(days=delta)

    timestamps = {}
    for uid in inbox.search(date):
        if slack.emails.find_one({'uid': uid}):
            continue

        msg = inbox.process_uid(uid)
        slack.emails.insert_one(msg) 

        msg_args = {
            'group': msg['group'],
            'subject': msg['subject'],
            'from_': parse_from(msg),
            'body': msg['body'],
            'channel': False,
        }

        thread_id = msg['thread_id']
        if thread_id in timestamps:
            bot.post(**msg_args)
            continue

        x = slack.threads.find_one({'thread_id': thread_id})
        if x: 
            timestamps[thread_id] = x['ts']
            bot.post(**msg_args)
            continue

        msg_args['channel'] = True
        ts = bot.post(**msg_args)
        timestamps[thread_id] = ts
        slack.threads.insert_one({
            'ts': ts, 
            'thread_id': thread_id, 
            'subject': msg['subject'],
            'tags': msg['tags'],
            'from': msg['from'],
            'group': msg['group'],
            'date': msg['date'],
        })


if __name__ == '__main__':
    main()

