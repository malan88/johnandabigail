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


def splitkey(key):
    """Split the key, return it as two ints."""
    key = [int(el) for el in key.split(':')]
    return key[0], key[1]


def incrementkey(key):
    """Increment the key."""
    links = getlinks()
    fnum, pnum = splitkey(key)
    lines = getlines(links[fnum])
    if len(lines) <= pnum + 1:
        pnum = 0
        fnum = (fnum + 1) % len(links)
    else:
        pnum += 1
    return f'{fnum}:{pnum}'


def updatekey(key):
    """Update the key in the dynamodb table with `key`"""
    key = incrementkey(key)
    table = gettable()
    table.update_item(
        Key={'id': 0},
        UpdateExpression="set k=:k",
        ExpressionAttributeValues={
            ':k': key
        }
    )


def getfiles():
    with open('jsonlist.json', 'rt') as fin:
        files = json.load(fin)
    return files


def getlinks():
    """Get the file list from the json list, prepend the url for the repo."""
    files = getfiles()
    links = []
    for f in files:
        links.append(LETTERS + f)
    links.sort()
    return links


def getlines(f):
    """Get all the lines from the json file."""
    http = urllib3.PoolManager()
    raw = http.request('GET', f).data.decode('utf-8')
    lines = json.loads(raw)
    return lines


def getlastdata():
    table = gettable()
    resp = table.get_item(Key={'id': 1})
    resp = resp['Item']
    return resp['sid'], resp['timelastsent']


def updatelastdata(sid='nosid'):
    """Update the last tweet data in dynamodb"""
    table = gettable()
    table.update_item(
        Key={'id': 1},
        UpdateExpression="set timelastsent=:t, sid=:s",
        ExpressionAttributeValues={
            ':t': int(time.time()),
            ':s': str(sid)
        }
    )


def tweet(tweet_to_send, sid='nosid'):
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
        if sid and sid != 'nosid':
            status = api.update_status(tweet_to_send, in_reply_to_status_id=sid)
        else:
            status = api.update_status(tweet_to_send)
    except RateLimitError:
        sys.exit('Hit a rate limit')
    return status.id


def gettweet():
    """Get the key, split it, and the current tweet, as well as the sid and
    timelastsent of the other tweet"""
    key = getkey()
    file, line = splitkey(key)
    links = getlinks()
    filename = links[file]
    lines = getlines(filename)
    tweet = lines[line]
    sid, timelastsent = getlastdata()
    if line >= len(lines) - 1:
        # we're at the end of the file, so the next tweet should be the
        # beginning of a new thread
        sid = 'nosid'

    return {'tweet': tweet, 'key': key, 'sid': sid, 'time': float(timelastsent)}


def main(p=False):
    """This is the main route. Gets tweet data and uses it to determine
    what to tweet.
    """
    tw = gettweet()
    sid = 'nosid' # placeholder in case we're updating with p
    if p:
        print(tw['tweet'])
    else:
        sid = tweet(tw['tweet'], tw['sid'])

    updatekey(tw['key'])
    updatelastdata(sid)

    return True, tw


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--print",
                        help="Just print to screen instead of tweeting",
                        action="store_true")
    args = parser.parse_args()
    main(args.print)
