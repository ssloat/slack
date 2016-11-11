from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, Integer

import re
import requests
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser

engine = create_engine('sqlite:///wheatonslack.db') #, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

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


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    group = Column(String)
    topic = Column(String)
    link = Column(String)
    subject = Column(String)
    body = Column(String)
    author = Column(String)

    def __init__(self, item):
        self.group, self.topic = item.find('guid').text.split('/')[-2:]
        self.link = item.find('link').text.split('/')[-1]

        hp = HTMLParser()

        self.subject = hp.unescape(item.find('title').text).strip()
        self.body = hp.unescape(
            item.find('description').text.replace(' Sent from my iPhone', '')
        ).strip()
        self.author = " ".join(
            hp.unescape(item.find('author').text).strip().splitlines()
        )

        if 'Re:' in self.subject:
            match = re.match('(.*?)( >)?\s+On .* wrote: .*', self.body)
            if match:
                self.body = match.group(1)
 

    @staticmethod
    def is_new_topic(msg):
        return not bool(
            session.query(Message).filter(Message.topic==msg.topic).first()
        )

    @staticmethod
    def is_new(msg):
        return not bool(
            session.query(Message).filter(Message.id==msg.id).first()
        )

    @staticmethod
    def add(msg):
        session.add(msg)
        session.commit()

Base.metadata.create_all(engine)

