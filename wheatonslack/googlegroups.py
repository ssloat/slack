import requests
import logging
import datetime
import pytz
from bs4 import BeautifulSoup

from wheatonslack.message import Message
 
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

class GroupsChecker(object):
    groups = [
#        'sloat-slackbot-testing', 
        'wheaton-soccer', 
        'wheaton-ultimate',
    ]

    def __init__(self, user, pwd, db_session, num):
        self.db_session = db_session
        self.web_session = SessionGoogle(user, pwd)
        self.num = num

        self.next_check = datetime.datetime.now()

    def check_groups(self, bot, post=True):
        if datetime.datetime.now() > self.next_check:

            for group in self.groups:
                logging.info("%s: checking %s" % (str(datetime.datetime.now()), group) )
                self.check_group(bot, group, post)

            self.next_check = self._next_check()


    def check_group(self, bot, group, post=True):
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
                if msg.author == 'Rebekah Sides':
                    # sorry Rebekah - not interested in your messages
                    channel = ''

                if len(msg.body) >= 250:
                    text = "%s\nFull message: https://groups.google.com/d/msg/%s/%s/%s" % (
                        text, msg.topic.group, msg.topic.name, msg.link
                    )

            self.db_session.add(msg)
            self.db_session.commit()

            if post:
                bot.post(
                    bot.channel_ids[ bot.slack_channels[group] ],
                    '%s[%d]From %s: %s' % (channel, msg.topic.id, msg.author, text),
                )

            else:
                logging.info(
                    '%s[%d]From %s: %s' % (channel, msg.topic.id, msg.author, text)
                )

    def _next_check(self):
        cst = pytz.timezone('America/Chicago')
        cst_now = pytz.utc.localize(datetime.datetime.now()).astimezone(cst)

        target = cst_now + datetime.timedelta(minutes=5)
        if target.hour < 7:
            target = target.replace(hour=7, minute=0, second=0)

        elif target.hour >= 22 or target.hour < 11:
            target = target + datetime.timedelta(minutes=15)

        return target.astimezone(pytz.utc).replace(tzinfo=None)
 
