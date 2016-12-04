from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey

import re
from HTMLParser import HTMLParser

Base = declarative_base()


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    link = Column(String)
    body = Column(String)
    author = Column(String)

    topic = relationship('Topic')

    def __init__(self, topic, link, body, author):
        self.topic = topic
        self.link = link
        self.body = body
        self.author = author

    @staticmethod
    def query_or_new(session, item):
        hp = HTMLParser()

        topic = Topic.query_or_new(session, item)
        link = item.find('link').text.split('/')[-1]

        body = hp.unescape(
            item.find('description').text.replace(' Sent from my iPhone', '')
        ).strip()

        match = re.match('(.*?)( >)?\s+On .* wrote: .*', body)
        if match:
            body = match.group(1)

        author = " ".join(
            hp.unescape(item.find('author').text).strip().splitlines()
        )

        if not topic.id:
            return Message(topic, link, body, author)

        m = session.query(Message).filter(
            Message.topic_id==topic.id,
            Message.link==link,
        ).first()

        if m:
            return m

        return Message(topic, link, body, author)

class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    group = Column(String)
    name = Column(String)
    subject = Column(String)

    def __init__(self, group, name, subject):
        self.group = group
        self.name = name
        self.subject = subject

    @staticmethod
    def query_or_new(session, item):
        group, name = item.find('guid').text.split('/')[-2:]

        t = session.query(Topic).filter(
            Topic.group==group,
            Topic.name==name,
        ).first()

        if t:
            return t

        subject = (
            HTMLParser()
                .unescape(item.find('title').text)
                .strip()
                .replace('[wheaton-ultimate] ', '')
        )
        return Topic(group, name, subject)

    def link(self):
        return "https://groups.google.com/forum/#!category-topic/%s/%s" % (
            self.group, self.name
        )


def get_session(name):
    engine = create_engine('sqlite:///'+name)#, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    Base.metadata.create_all(engine)

    return session

if __name__ == '__main__':
    get_session()
