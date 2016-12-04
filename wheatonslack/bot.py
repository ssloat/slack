import os
import re
import smtplib
import logging

from slackclient import SlackClient

from wheatonslack.message import Message, Topic

logger = logging.getLogger(__name__)

BOT_ID = os.environ.get('BOT_ID')
SENDER_USER = os.environ.get('SENDER_USER')
SENDER_PASS = os.environ.get('SENDER_PASS')

class Bot(object):
    def __init__(self, db_session):
        self.db_session = db_session

        self.slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
        self.commands = [
            CommandRecent(),
            CommandLink(),
            CommandReplay(),
        ]

        self._init_channels()
        self._init_members()

    def _init_channels(self):
        channels = self.slack_client.api_call('channels.list', exclude_archived = 1)
        if not channels.get('ok', False):
            raise Exception('could not get channel list')

        self.channels = dict([(x['id'], x['name']) for x in channels['channels']])
        self.channel_ids = dict( (v, k) for k, v in self.channels.items() )

    def _init_members(self):
        """
        members = self.slack_client.api_call('users.list')
        if not members.get('ok', False):
            raise Exception('could not get user list')

        self.members = dict( (m['id'], User(m)) for m in members['members'] )
        """
        pass

    def post(self, channel_id, text):
        self.slack_client.api_call(
            "chat.postMessage", 
            channel=channel_id,
            text=text,
            as_user=True
        )

    def rtm_post(self, channel_id, text):
        self.slack_client.rtm_send_message(channel_id, text)


    def parse_slack_output(self, slack_rtm_output):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """

        if not slack_rtm_output or len(slack_rtm_output) == 0:
            return

        outputs = [x for x in slack_rtm_output if x and 'text' in x]
        for output in outputs:
            output['text'] = output['text'].lower()
            logger.debug(output)

            if 'user' not in output:
                """
                    message without user is: a post from googlebot
                """
                continue

            user_id = output['user']
            channel_id = output['channel']

            if channel_id in self.channels:
                """
                    googlebot only responds to direct messages
                """
                """
                if '<@%s>' % (BOT_ID) in output['text']:
                    self.rtm_post(
                        channel_id=channel_id,
                        text="<@%s> Let's chat in private" % ( 
                            self.members[user_id].name,
                        )
                    )
                """

                continue

            logger.info(output)

            matched = False
            for cmd in self.commands:
                match = cmd.match(output)
                if match:
                    text = cmd.run(match, self.db_session)
                    self.rtm_post(channel_id, texts)

                    matched = True
                    break

            if not matched:
                self.rtm_post(
                    channel_id=channel_id,
                    text="I don't know that one.  I can:\n%s" % (
                        "\n".join([x.help_text for x in self.commands])
                    ),
                )


class CommandRecent(object):
    help_text = 'recent [n]'

    def match(self, output):
        return re.search('recent [n]', output['text'])

    def run(self, match, db):
        n = int(match.group(1))

        topics = db.query(Topic).filter(
            Topic.group=='wheaton-ultimate'
        ).order_by(Topic.id).all()

        texts = []
        for topic in reversed(topics[-1*n:]):
            m = db.query(Message).filter(
                Message.topic_id==topic.id
            ).order_by(Message.id).first()

            texts.append(
                "[%d] From %s:  %s" % (topic.id, m.author, topic.subject)
            )

        return "\n".join(texts)


class CommandLink(object):
    help_text = 'link [n]'

    def match(self, output):
        return re.search('link (\d+)', output['text'])

    def run(self, match, db):
        n = int(match.group(1))

        topic = db.query(Topic).filter(Topic.id==n).first()
        return topic.link()

class CommandReplay(object):
    help_text = 'replay [n]'

    def match(self, output):
        return re.search('replay (\d+)', output['text'])

    def run(self, match, db):
        n = int(match.group(1))

        msgs = db.query(Message).filter(Message.topic_id==n).order_by(Message.id).all()

        texts = ["%s:" % (msgs[0].topic.subject)]
        texts.extend([
            "From %s: %s" % (msg.author, msg.body)
            for msg in msgs
        ])

        return "\n".join(texts)




class User(object):
    def __init__(self, config):
        self.config = config
        self.id = config['id']
        self.name = config['name']

    @property
    def real_name(self):
        return self.config['profile']['real_name']

    @property
    def email(self):
        return self.config['profile']['email']

    def __repr__(self):
        return "<User: %s>" % self.real_name

