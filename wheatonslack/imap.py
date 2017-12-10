import imaplib
import email
import re
import chardet
import datetime
import time
import urllib

from HTMLParser import HTMLParser

class Inbox(object):
    def __init__(self, user, pwd, mongo, bot):
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(user, pwd)
        self.mail.select('inbox')

        self.uids = {}
        self.timestamps = {}
        self.threads = mongo['threads']
        self.emails = mongo['emails']
        self.bot = bot
        
    def run(self, date):

        result, data = self.mail.uid('search', None, "(SENTSINCE %s)" % date.strftime('%d-%b-%Y'))

        mail_ids = [uid for uid in data[0].split() if not self.is_processed(uid)]

        for uid in mail_ids:
            self.process_uid(uid)

    def process_uid(self, uid):
        thread_id, message = self.fetch_message(uid)

        if not message or 'List-ID' not in message:
            self.uids[uid] = True
            return

        txt = get_text(message) 
        if not txt:
            txt = '<Could not parse message>'

        body = self.parse_body(txt)

        subj = message['Subject'].replace('[wheaton-ultimate] ', '')
        msg = {
            'uid': uid,
            'thread_id': thread_id,
            'date': datetime.datetime.fromtimestamp(
                email.utils.mktime_tz(email.utils.parsedate_tz(message['Date']))
            ),
            'group': message['List-ID'][1:-1].replace('.googlegroups.com', ''),
            'from': message['From'],
            'body': body,
            'subject': "".join(subj.splitlines()),
        }

        self.post(msg, thread_id)
        self.emails.insert_one(msg)

    def channel_id(self, msg):
        group_map = {
            'wheaton-soccer': 'sports-soccer',
            'wheaton-ultimate': 'social',
        }
        return self.bot.channel_ids[ group_map.get(msg['group'], 'sloat-testing') ]
        #return self.bot.channel_ids['sloat-testing']

    def fetch_message(self, uid):
        result, data = self.mail.uid('fetch', uid, '(X-GM-THRID RFC822)')
        thread_id = re.match('.*X-GM-THRID (\d+)', data[0][0]).group(1)
        raw_email = data[0][1]

        return thread_id, email.message_from_string(raw_email)

    def is_processed(self, uid):
        if uid in self.uids or self.emails.find_one({'uid': uid}):
            self.uids['uid'] = True
            return True

        return False

    def parse_body(self, txt):
        lines = txt.splitlines()
        for n, line in list(enumerate(lines)):
            if line == '-- ':
                lines = lines[:n]
                break

        body = " ".join(lines)
        body = body.replace(' Sent from my iPhone', '')

        match = re.match('(.*?)( >)?\s+On .* wrote: .*', body)
        if match:
            body = match.group(1)

        return body

    def post_new(self, msg, channel=True):
        result = self.bot.post(
            self.channel_id(msg), 
            "%sFrom %s: %s\n%s" % (
                ('<!channel> ' if channel else ''),
                parse_from(msg), 
                msg['subject'],
                (msg['body'][:450]+'...' if len(msg['body']) > 600 else msg['body']),
            )
        )
        if len(msg['body']) > 600:
            self.bot.post(
                self.channel_id(msg), 
                "...%s" % msg['body'][450:],
                thread_ts=result['ts'],
            )

        return result['ts']

    def post(self, msg, thread_id):
        if thread_id not in self.timestamps:
            x = self.threads.find_one({'thread_id': thread_id})
            if not x: 
                ts = self.post_new(msg)
                self.timestamps[thread_id] = ts
                self.threads.insert_one({'thread_id': thread_id, 'ts': ts})

                return

            self.timestamps[thread_id] = x['ts']

        self.bot.post(
            self.channel_id(msg), 
            "From %s: %s" % (parse_from(msg), msg['body']), 
            thread_ts=self.timestamps[thread_id],
        )

    def post_unthreaded(self, msg, thread_id):
        if thread_id not in self.timestamps:
            x = self.threads.find_one({'thread_id': thread_id})
            if not x: 
                ts = self.post_new(msg)
                self.timestamps[thread_id] = ts
                self.threads.insert_one({'thread_id': thread_id, 'ts': ts})

                return

            self.timestamps[thread_id] = x['ts']
 
        if len(msg['subject']) > 30:
            msg['subject'] = "%s..." % msg['subject'][:30]

        self.post_new(msg, False)


def parse_from(msg): 
    addr = email.utils.parseaddr(msg['from'])

    subj = msg['subject']
    if subj[:4] != 'Re: ':
        subj = 'Re: '+subj

    subj = urllib.urlencode([('subject', msg['subject'])])
    subj = subj.replace('+', ' ')
    return '<mailto:%s?%s|%s>' % (addr[1], subj, addr[0]) 

def get_text(msg):
    text = ""
    if msg.is_multipart():
        html = None
        for part in msg.walk():
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            if part.get_content_charset() is None:
                charset = chardet.detect(str(part))['encoding']
            else:
                charset = part.get_content_charset()

            x = unicode(payload, str(charset), "ignore")
            x = x.encode('utf8','replace')
            
            if part.get_content_type() == 'text/plain':
                text = x

            elif part.get_content_type() == 'text/html':
                html = x

        if text != "": return text.strip()
        return text.strip() if html is None else html.strip()

    else:
        text = unicode(
            msg.get_payload(decode=True),
            msg.get_content_charset(),
            'ignore'
        ).encode('utf8','replace')

        return text.strip()
