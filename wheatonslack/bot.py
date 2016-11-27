import os
import smtplib
import logging

from slackclient import SlackClient

logger = logging.getLogger('wheatonslack.bot')

BOT_ID = os.environ.get('BOT_ID')
SENDER_USER = os.environ.get('SENDER_USER')
SENDER_PASS = os.environ.get('SENDER_PASS')

google_group_emails = {
    'sports-ultimate': 'wheaton-ultimate-abridged',
    'sports-soccer': 'wheaton-soccer',
    'prayerandpraise': 'p-and-p',
    'social': 'wheaton-ultimate',
    'sloat-testing': 'sloat-slackbot-testing',
}

class Bot(object):
    def __init__(self):
        self.slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

        self._init_channels()
        self._init_members()

    def _init_channels(self):
        channels = self.slack_client.api_call('channels.list', exclude_archived = 1)
        if not channels.get('ok', False):
            raise Exception('could not get channel list')

        self.channels = dict([(x['id'], x['name']) for x in channels['channels']])
        self.channel_ids = dict( (v, k) for k, v in self.channels.items() )
        self.slack_channels = dict( 
            (v, k) for k, v in google_group_emails.items()
        )

    def _init_members(self):
        members = self.slack_client.api_call('users.list')
        if not members.get('ok', False):
            raise Exception('could not get user list')

        self.members = dict( (m['id'], User(m)) for m in members['members'] )

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

        commands = [
            #'send email:  @googlebot announce: {subject}: {body}',
            'do nothing.',
        ]

        if not slack_rtm_output or len(slack_rtm_output) == 0:
            return

        for output in slack_rtm_output:
            if output and 'text' in output:
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

                self.rtm_post(
                    channel_id=channel_id,
                    text="I don't know that one.  I can:\n%s" % (
                        "\n".join(commands)
                    ),
                )


class Command(object):
    def __init__(self, text, user_id, channel_id):
        self.text = text
        self.user_id = user_id
        self.channel_id = channel_id

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

