import os
import smtplib

from slackclient import SlackClient

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


    def handle_command(self, cmd):
        user = self.members[cmd.user_id]
        channel = self.channels[cmd.channel_id]
        print channel, user.real_name, cmd.text

        if channel not in google_group_emails:
            self.post(
                channel_id=cmd.channel_id,
                text="<@%s>, this channel does not have a google group assigned" % user.name,
            )
            return


        if ':' not in cmd.text:
            self.post(
                channel_id=cmd.channel_id,
                text='<@%s>, please use format:  <subject>: <body>' % user.name,
            )
            return

        try:
            subject, body = cmd.text.split(':')

        except ValueError:
            self.post(
                channel_id=cmd.channel_id,
                text='<@%s>, too many :\'s.  please use format:  <subject>: <body>' % user.name,
            )
            return

        to_addr = '%s@googlegroups.com' % google_group_emails[channel]

        message = """From: {from_name} on Slack <{from_email}>
To: {to_addr}
Subject: {subject}
Reply-To: {reply_email}
Return-Path: {return_path}

{body}
""".format(
            from_name = user.real_name,
            from_email = user.email,
            to_addr = to_addr,
            subject = subject,
            reply_email = user.email,
            return_path = user.email,
            body = body,
        )

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_USER, SENDER_PASS)
        server.sendmail(user.email, [to_addr], message)
        server.quit()

        self.post(
            channel_id=cmd.channel_id,
            text='<@%s>, your message has been announced' % user.name,
        )


    def parse_slack_output(self, slack_rtm_output):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """

        commands = [
            'send email:  @googlebot announce: {subject}: {body}',
        ]

        if not slack_rtm_output or len(slack_rtm_output) == 0:
            return

        for output in slack_rtm_output:
            if output and 'text' in output and '<@%s>' % (BOT_ID) in output['text']:
                user_id = output['user']
                channel_id = output['channel']

                if '<@%s> announce ' % (BOT_ID) in output['text']:
                    return Command(
                        output['text'].split('<@%s> announce ' % BOT_ID)[1].strip(), 
                        user_id, 
                        channel_id
                    )

                self.post(
                    channel=channel_id,
                    text="<@%s> I don't know that one.  I can:\n%s" % (
                        self.members[user_id].name, 
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

