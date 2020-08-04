import re, time, json, os, math, sys
import textwrap, argparse
import boto3, urllib3, tweepy
from tweepy import RateLimitError, TweepError

TABLE = 'adams-family'
LETTERS = 'https://johnandabigail.netlify.app/'
TIME_BETWEEN_TWEETS = 60 * 10 - 10

def gettable():
    """Just get the dynamodb table."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE)
    return table


def getkey():
    """Get the key as a string"""
    table = gettable()
    resp = table.get_item(Key={'id': 0})
    key = resp['Item']['k']
    return key


def incrementkey(key, files):
    """Increment the key."""
    fnum, pnum = splitkey(key)
    paragraphs = getparagraphs(files[fnum])
    if len(paragraphs) <= pnum + 1:
        pnum = 0
        fnum = (fnum + 1) % len(files)
    else:
        pnum += 1
    return f'{fnum}:{pnum}'


def updatekey(key):
    """Update the key in the dynamodb table with `key`"""
    table = gettable()
    table.update_item(
        Key={'id': 0},
        UpdateExpression="set k=:k",
        ExpressionAttributeValues={
            ':k': key
        }
    )


def splitkey(key):
    """Split the key, return it as two ints."""
    key = [int(el) for el in key.split(':')]
    return key[0], key[1]


def getparagraphs(f):
    """Get all the paragraphs as a list without empty strings."""
    http = urllib3.PoolManager()
    paragraphs = http.request('GET', f).data.decode('utf-8').splitlines()
    return list(filter(None, map(str.strip, paragraphs)))


def getfiles():
    """Get the file list from the json list, prepend the url for the repo."""
    with open('list.json', 'rt') as fin:
        ls = json.load(fin)
    links = []
    for f in ls:
        links.append(LETTERS + f)
    links.sort()
    return links


def getnext(key, files):
    """Get the next tweet paragraph"""
    fnum, pnum = splitkey(key)
    f = files[fnum]
    paragraphs = getparagraphs(f)
    p = paragraphs[pnum]
    return p


def splittweet(tweet):
    """Split a paragraph into an array for tweeting"""
    if len(tweet) <= 270:
        tweets = [tweet]
    else:
        #tweets = textwrap.wrap(tweet, 270, break_long_words=False)
        tweets = re.split('(?<=[.!?—])[ —]+', tweet)
        newarr = []
        for t in tweets:
            # check to make sure each tweet is under 270, otherwise wrap it.
            if len(t) <= 270:
                newarr.append(t)
            else:
                wrapped = textwrap.wrap(t, 270, break_long_words=False)
                newarr += wrapped
        tweets = newarr
    return tweets


def get_current_tweet():
    """Get the current tweet info"""
    table = gettable()
    resp = table.get_item(Key={'id': 1})
    return resp['Item']


def update_dynamo(lines, idx, sid=None):
    """Update the current_tweet data in dynamodb"""
    table = gettable()
    table.update_item(
        Key={'id': 1},
        UpdateExpression="set tweet=:k, idx=:i, timelastsent=:t, sid=:s",
        ExpressionAttributeValues={
            ':k': lines,
            ':i': idx,
            ':t': int(time.time()),
            ':s': str(sid)
        }
    )


def tweet(tweet, sid=None):
    """Send out a tweet."""
    auth = tweepy.OAuthHandler(
        os.environ['TWITTER_CONSUMER_KEY'],
        os.environ['TWITTER_CONSUMER_SECRET_KEY']
    )
    auth.set_access_token(
        os.environ['TWITTER_ACCESS_TOKEN'],
        os.environ['TWITTER_ACCESS_SECRET']
    )
    api = tweepy.API(auth)
    try:
        if sid:
            status = api.update_status(tweet, in_reply_to_status_id=sid)
        else:
            status = api.update_status(tweet)
    except RateLimitError:
        sys.exit('Hit a rate limit')
    return status.id


def fix_current_tweet(current_tweet):
    """Simple helper function that doesn't even seem to work perfectly, for
    generating the current_tweet dictionary.
    """
    if not 'idx' in current_tweet:
        current_tweet['idx'] = len(current_tweet['tweet'])
    else:
        # idx needs to not be a Decimal
        current_tweet['idx'] = int(current_tweet['idx'])
    if not 'sid' in current_tweet:
        current_tweet['sid'] = 'nosid'
    if not 'timelastsent' in current_tweet:
        current_tweet['timelastsent'] = time.time() - 10 * 60
    else:
        current_tweet['timelastsent'] = float(current_tweet['timelastsent'])
    return current_tweet


def check_paragraph(key):
    """Companion to set_paragraph, just check if it exists."""
    try:
        files = getfiles()
        p = getnext(key, files)
    except KeyError:
        print('wah wah wah')
        print('key bad')
        return False
    return True


def set_paragraph(key):
    """To reset, or set the paragraph first check that it exists, then set it,
    then update the dynamo to bypass the paragraph continuation switch in main()
    """
    good = check_paragraph(key)
    if good:
        updatekey(key)
        update_dynamo([], 1000, 'nosid')


def main(nowait=False):
    """This is the main route. Gets current_tweet data and uses it to determine
    what to tweet.
    """
    current_tweet = fix_current_tweet(get_current_tweet())
    tweeted = False

    if current_tweet['idx'] + 1 <= len(current_tweet['tweet']):
        # The current tweet is still live, that is to say: we're still tweeting
        # one long paragraph
        content = current_tweet['tweet']
        idx = current_tweet['idx']
        sid = current_tweet['sid']
        sid = tweet(content[idx], sid)
        update_dynamo(content, idx+1, sid)
        tweeted = True
    elif nowait or time.time() - current_tweet['timelastsent'] >= TIME_BETWEEN_TWEETS:
        # This is a new paragraph
        key = getkey()
        files = getfiles()
        content = getnext(key, files)
        content = splittweet(content)
        idx = 0
        fnum, pnum = splitkey(key)
        sid = current_tweet['sid']
        if pnum > 0 and sid != 'nosid':
            # only tweet without the sid (that is to say the only time you're
            # not creating a thread) is when you are starting a new letter
            # (pnum=0)
            sid = tweet(content[idx], sid)
        else:
            sid = tweet(content[idx])
        key = incrementkey(key, files)
        updatekey(key)
        update_dynamo(content, idx+1, sid)
        tweeted = True

    current_tweet = fix_current_tweet(get_current_tweet())
    return tweeted, current_tweet


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--loop", help="Loop every 10 minutes to tweet",
                        action="store_true")
    parser.add_argument("-w", "--nowait",
                        help="Don't wait between tweets, for testing purposes",
                        action="store_true")
    parser.add_argument("-p", "--paragraph", help="Set the fnum:pnum",
                        action="store", type=str)
    args = parser.parse_args()
    if args.paragraph:
        set_paragraph(args.paragraph)
    elif args.loop:
        while True:
            main(args.nowait)
            time.sleep(60*10)
    else:
        print(main(args.nowait))
