import sys
import argparse
import socket
import logging
import os
import time
import datetime
from bs4 import BeautifulSoup

from wheatonslack.bot import Bot
from wheatonslack.message import Message, SessionGoogle

NUM = 15
BOT = None
SESSION = None

def check_groups(post=True):
    groups = [
#        'sloat-slackbot-testing', 
        'wheaton-soccer', 
        'wheaton-ultimate',
        'wheaton-ultimate-abridged',
    ]

    for group in groups:
        logging.info("%s: checking %s" % (str(datetime.datetime.now()), group) )
        check_group(group, post)


def check_group(group, post=True):
    url = 'https://groups.google.com/forum/feed/%s/msgs/rss.xml?num=%d' % (group, NUM)

    soup = BeautifulSoup(SESSION.get(url), 'html.parser')

    items = soup.find_all('item')
    for item in items[::-1]:
        msg = Message(item)
        if not Message.is_new(msg):
            continue

        Message.add(msg)

        if 'Re:' in msg.subject:
            text = msg.body
            channel = ''
        else:
            text = "%s\n%s" % (msg.subject, msg.body)
            channel = '<!channel> '

            if len(msg.body) >= 290:
                text = "%s\nFull message: https://groups.google.com/d/msg/%s/%s/%s" % (
                    text, msg.group, msg.topic, msg.link
                )

        if post:
            BOT.post(
                BOT.channel_ids[ BOT.slack_channels[group] ],
                '%sFrom %s: %s' % (channel, msg.author, text),
            )
                
lock_socket = None
def is_lock_free():
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_id = 'ssloat.listen_rss'
        lock_socket.bind('\0' + lock_id)
        logging.debug("Acquired lock %r" % lock_id)
        return True
    except socket.error:
        logging.info("Failed to acquire lock %r" % lock_id)
        return False

def main():
    global NUM
    global BOT
    global SESSION

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--prime', 
        help='Prime db with existing messages',
        action='store_true',
    )
    parser.add_argument(
        '-n', '--num', 
        help='Number of messages to retrieve',
        type=int,
    )

    args = parser.parse_args()
    if args.num:
        NUM = args.num

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
    )
    if not is_lock_free():
        sys.exit()

    BOT = Bot()
    SESSION = SessionGoogle( 
        os.environ.get('SENDER_USER'), 
        os.environ.get('SENDER_PASS')
    )
    if args.prime:
        check_groups(False)
        sys.exit(0)

    while True:
        check_groups()

        time.sleep(180)



if __name__ == '__main__':
    main()
