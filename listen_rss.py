import requests
import sys
import argparse
import socket
import logging
import os
import time
import datetime
import pytz
from bs4 import BeautifulSoup

from wheatonslack.bot import Bot
from wheatonslack.message import Message, get_session

class SessionGoogle(object):
    url_login = "https://accounts.google.com/ServiceLogin"
    url_auth = "https://accounts.google.com/ServiceLoginAuth"
    def __init__(self, login, pwd):
        self.session = requests.session()

        login_html = self.session.get(SessionGoogle.url_login)
        soup_login = BeautifulSoup(login_html.content, 'html.parser')

        my_dict = {}
        for u in soup_login.find('form').find_all('input'):
            if u is None:
                continue

            if u.has_attr('value'):
                my_dict[u['name']] = u['value']

        # override the inputs without login and pwd:
        my_dict['Email'] = login
        my_dict['Passwd'] = pwd

        self.session.post(SessionGoogle.url_auth, data=my_dict)

    def get(self, url):
        return self.session.get(url).text

class Checker(object):
    groups = [
        'sloat-slackbot-testing', 
        'wheaton-soccer', 
        'wheaton-ultimate',
        'wheaton-ultimate-abridged',
    ]

    def __init__(self, db_session, web_session, bot, num):
        self.db_session = db_session
        self.web_session = web_session
        self.bot = bot
        self.num = num

    def check_groups(self, post=True):
        for group in self.groups:
            logging.info("%s: checking %s" % (str(datetime.datetime.now()), group) )
            self.check_group(group, post)


    def check_group(self, group, post=True):
        url = 'https://groups.google.com/forum/feed/%s/msgs/rss.xml?num=%d' % (group, self.num)

        soup = BeautifulSoup(self.web_session.get(url), 'html.parser')

        items = soup.find_all('item')
        for item in items[::-1]:
            msg = Message.query_or_new(self.db_session, item)
            if msg.id is not None:
                continue

            if msg.topic.id is not None:
                text = msg.body
                channel = ''
            else:
                text = "%s\n%s" % (msg.topic.subject, msg.body)
                channel = '<!channel> '

                if len(msg.body) >= 290:
                    text = "%s\nFull message: https://groups.google.com/d/msg/%s/%s/%s" % (
                        text, msg.topic.group, msg.topic.name, msg.link
                    )

            self.db_session.add(msg)
            self.db_session.commit()

            if post:
                self.bot.post(
                    self.bot.channel_ids[ self.bot.slack_channels[group] ],
                    '%s[%d]From %s: %s' % (channel, msg.topic.id, msg.author, text),
                )

            else:
                print '%s[%d]From %s: %s' % (channel, msg.topic.id, msg.author, text)
                
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
    parser.add_argument(
        '--db', 
        help='DB filename',
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
    )
    if not is_lock_free():
        sys.exit()

    checker = Checker(
        get_session(args.db or 'wheatonultimate.db'),
        SessionGoogle( 
            os.environ.get('SENDER_USER'), 
            os.environ.get('SENDER_PASS')
        ),
        Bot(),
        (args.num or 15)
    )

    if args.prime:
        checker.check_groups(False)
        sys.exit(0)

    cst = pytz.timezone('America/Chicago')
    while True:
        checker.check_groups()

        now = pytz.utc.localize(datetime.datetime.now()).astimezone(cst)
        if now.hour < 7:
            target = now.replace(hour=7, minute=0, second=0)
            time.sleep(
                (target - now).total_seconds()
            )

        elif now.hour >= 22 or now.hour < 11:
            time.sleep(1200)

        else:
            time.sleep(600)



if __name__ == '__main__':
    main()
