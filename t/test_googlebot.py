
from config import GROUPS
from wheatonslack.googlegroups import GroupsChecker, SessionGoogle
#from wheatonslack.bot import Bot
from wheatonslack.message import get_session, Message, Topic

from nose.tools import assert_equals
from mock import MagicMock

class TestClass:
    def setUp(self):
        GROUPS['group'] = 'testing'
        self.db_session = get_session(':memory:')

        self.checker = GroupsChecker('user', 'pass', self.db_session, 15)
        self.checker.web_session = MagicMock()
        self.bot = MagicMock()

    def tearDown(self):
        self.db_session.close()

    def test_checker(self):
        self.checker.web_session.get.return_value = "\n".join(ITEMS[-2:])
        self.checker.check_group(self.bot, 'group', True)

        m1 = self.db_session.query(Message).filter(Message.id==1).first()
        assert_equals(m1.topic.subject, 'soccer // 545pm // north of marianos')
        
        calls = self.bot.post.call_args_list
        assert_equals([x[0][1] for x in calls], TEXTS[:2])


        #Test that when additional messages are returned, we don't reannounce 
        self.checker.web_session.get.return_value = "\n".join(ITEMS)
        self.bot = MagicMock()
        self.checker.check_group(self.bot, 'group', True)

        calls = self.bot.post.call_args_list
        assert_equals([x[0][1] for x in calls], TEXTS[2:])

        messages = self.db_session.query(Message).all()
        assert_equals(len(messages), len(ITEMS))


        #Test we don't re-announce any messages already in db
        self.checker.web_session.get.return_value = "\n".join(ITEMS)
        self.bot = MagicMock()
        self.checker.check_group(self.bot, 'group', True)

        assert not self.bot.post.called


TEXTS = [
    """<!channel> [1]From wheatonultimate.slack@gmail.com (me): soccer // 545pm // north of marianos
i think we should have enough for a small game tomorrow night, but let's take a count to be sure. thanks""",
    """[1]From Stephen Sloat: we've got me, Jimmy, Megan, Molly, and Mark. anyone else want to play with us?""",
    """[1]From Stephen Sloat: we lost Jimmy but gained Peace, Okerman and Josh V, so we have 3 on 4. come on out, we're playing!""",
    """[1]From Josh Okerman: I will play. That's 3 on 3. -Josh""",
    """<!channel> [2]From Stephen Sloat: Soccer //tonight @545 // marianos
Peace , Megan , Rocky want to try playing tonight . I'll be there too. Come join us !""",
    """[2]From jgmottice: i'll come!""",
]
 
ITEMS = [
    """<item>
<title>Re: Soccer //tonight @545 // marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/hzDGXgs53SY/5_wymfUiAAAJ
</link>
<description>
i'll come! On Thu, Nov 10, 2016 at 3:48 PM, Stephen Sloat <stephe...@gmail.com> wrote: > Peace , Megan , Rocky want to try playing tonight . I'll be there too. > Come join us ! > > -- > You received this message because you are subscribed to the Google Groups > "Wheaton Adult Rec Soccer"
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/hzDGXgs53SY
</guid>
<author>jgmottice</author>
<pubDate>Thu, 10 Nov 2016 21:50:26 UTC</pubDate>
</item>
""",
    """<item>
<title>Soccer //tonight @545 // marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/hzDGXgs53SY/re5-ndgiAAAJ
</link>
<description>
Peace , Megan , Rocky want to try playing tonight . I'll be there too. Come join us !
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/hzDGXgs53SY
</guid>
<author>Stephen Sloat</author>
<pubDate>Thu, 10 Nov 2016 21:48:21 UTC</pubDate>
</item>
""",
    """<item>
<title>Re: soccer // 545pm // north of marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/7tFaKGsa0gI/qm8yN7TuCAAJ
</link>
<description>
I will play. That's 3 on 3. -Josh On Thu, Nov 3, 2016 at 2:07 PM, Stephen Sloat <stephe...@gmail.com> wrote: > we've got me, Jimmy, Megan, Molly, and Mark. anyone else want to play > with us? > > > On Wed, Nov 2, 2016 at 6:39 PM Stephen Sloat on Slack < > wheatonult...@gmail.com> wrote: > >> i
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/7tFaKGsa0gI
</guid>
<author>Josh Okerman</author>
<pubDate>Thu, 03 Nov 2016 21:18:26 UTC</pubDate>
</item>
""",
    """<item>
<title>Re: soccer // 545pm // north of marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/7tFaKGsa0gI/Voa98HjuCAAJ
</link>
<description>
we lost Jimmy but gained Peace, Okerman and Josh V, so we have 3 on 4. come on out, we're playing! On Thu, Nov 3, 2016 at 2:07 PM Stephen Sloat <stephe...@gmail.com> wrote: > we've got me, Jimmy, Megan, Molly, and Mark. anyone else want to play > with us? > > > On Wed, Nov 2, 2016 at 6:39 PM
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/7tFaKGsa0gI
</guid>
<author>Stephen Sloat</author>
<pubDate>Thu, 03 Nov 2016 21:14:11 UTC</pubDate>
</item>
""",
    """<item>
<title>Re: soccer // 545pm // north of marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/7tFaKGsa0gI/xxTT2pfnCAAJ
</link>
<description>
we've got me, Jimmy, Megan, Molly, and Mark. anyone else want to play with us? On Wed, Nov 2, 2016 at 6:39 PM Stephen Sloat on Slack < wheatonult...@gmail.com> wrote: > i think we should have enough for a small game tomorrow night, but let's > take a count to be sure. thanks > > -- > You
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/7tFaKGsa0gI
</guid>
<author>Stephen Sloat</author>
<pubDate>Thu, 03 Nov 2016 19:08:07 UTC</pubDate>
</item>
""",
    """<item>
<title>soccer // 545pm // north of marianos</title>
<link>
https://groups.google.com/d/msg/wheaton-soccer/7tFaKGsa0gI/hnoLFc2nCAAJ
</link>
<description>
i think we should have enough for a small game tomorrow night, but let's take a count to be sure. thanks
</description>
<guid isPermaLink="true">
https://groups.google.com/d/topic/wheaton-soccer/7tFaKGsa0gI
</guid>
<author>wheatonultimate.slack@gmail.com (me)</author>
<pubDate>Wed, 02 Nov 2016 23:39:07 UTC</pubDate>
</item>
"""
]
