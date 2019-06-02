import re


def has_time(s):
    return re.search(r'(\d+(:\d+)? *[ap]m?)', s) or re.search(r'(\d+:\d\d)', s) or re.search(r' at \d+', s)

def msg_tags(msg):
    subject = msg['subject'].lower()
    body = msg['body'].lower()

    tags = []
    if has_time(msg['subject']):
        tags.append('event')
        if any([x in subject for x in ('monroe', 'scripture', 'lawson')]):
            tags.append('ultimate')

    else: 
        if any([x in subject for x in ('rent', 'tenant', 'housing', 'roommate')]):
            tags.append('housing')

        if 'looking for ' in subject:
            tags.append('looking for')

    return tags


