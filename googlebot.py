import sys
import argparse
import socket
import logging
import os
import time

from wheatonslack.bot import Bot
from wheatonslack.message import get_session
from wheatonslack.googlegroups import GroupsChecker
               
lock_socket = None
def is_lock_free():
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_id = 'ssloat.googlebot'
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
        format='%(asctime)s %(name) %(levelname)-8s %(message)s',
    )
    if not is_lock_free():
        sys.exit()

    checker = GroupsChecker(
        os.environ.get('SENDER_USER'), 
        os.environ.get('SENDER_PASS'),
        get_session(args.db or 'wheatonultimate.db'),
        (args.num or 15)
    )

    if args.prime:
        checker.check_groups(bot, False)
        sys.exit(0)

    bot = Bot()
    bot.slack_client.rtm_connect()
    while True:
        checker.check_groups(bot)

        slack_out = bot.slack_client.rtm_read()
        bot.parse_slack_output(slack_out)

        time.sleep(1)



if __name__ == '__main__':
    main()
