import requests
import sys
import socket
import logging
import os
import re
import time
import datetime
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser

from wheatonslack.bot import Bot


class SessionGoogle:
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

class Messages(object):
    '''
        this should be something other than a file
    '''
    fn = 'guids.txt'
    def __init__(self):
        self.messages = set()
        with open(Messages.fn, 'r') as fh:
            lines = fh.read().splitlines()
            for guid in lines:
                self.messages.add(guid)

    def seen(self, guid):
        return guid in self.messages

    def add(self, guid):
        with open(Messages.fn, 'a') as fh:
            fh.write("%s\n" % guid)

        self.messages.add(guid)

def check_group(bot, messages, group):
    url = 'https://groups.google.com/forum/feed/%s/msgs/rss.xml?num=15' % group

    soup = BeautifulSoup(session.get(url), 'html.parser')

    items = soup.find_all('item')
    for item in items:
        guid = item.find('link').text
        if messages.seen(guid):
            continue

        messages.add(guid)

        hp = HTMLParser()

        title = hp.unescape(item.find('title').text).strip()
        msg = hp.unescape(item.find('description').text).strip()
        author = " ".join(
            hp.unescape(item.find('author').text).strip().splitlines()
        )

        is_new = True
        if title[:3] == 'Re:':
            is_new = False
            match = re.match('(.*?) On .* wrote: .*', msg)
            if match:
                msg = match.group(1)

        bot.post(
            bot.channel_ids[ bot.slack_channels[group] ],
            '%sFrom %s: %s\n%s' % (
                ('<!channel> ' if is_new else ''),
                author, title, msg
            ),
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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    groups = [
        'sloat-slackbot-testing', 
        'wheaton-soccer', 
        'wheaton-ultimate',
        'wheaton-ultimate-abridged',
    ]

    if not is_lock_free():
        sys.exit()

    messages = Messages()
    session = SessionGoogle(
        os.environ.get('SENDER_USER'), 
        os.environ.get('SENDER_PASS')
    )
    bot = Bot()
    while True:
        for group in groups:
            logging.info("%s: checking %s" % (str(datetime.datetime.now()), group) )
            check_group(bot, messages, group)

        time.sleep(180)


