import re
import textwrap
import boto3
import time
import urllib3
import json
import argparse
import tweepy
import os
import math
import sys

TABLE = 'adams-family'
LETTERS = 'https://johnandabigail.netlify.app/'
TIME_BETWEEN_TWEETS = 60 * 10

def gettable():
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
    with open('list.json', 'rt') as fin:
        ls = json.load(fin)
    links = []
    for f in ls:
        links.append(LETTERS + f)
    links.sort()
    return links


def getnext(key, files):
    fnum, pnum = splitkey(key)
    f = files[fnum]
    paragraphs = getparagraphs(f)
    p = paragraphs[pnum]
    return p


def splittweet(tweet):
    if len(tweet) <= 270:
        tweets = [tweet]
    else:
        tweets = re.split('(?<=[.!?—])[ —]+', tweet)
        newarr = []
        for t in tweets:
            if len(t) <= 270:
                newarr.append(t)
            else:
                wrapped = textwrap.wrap(t, 270, break_long_words=False)
                newarr += wrapped
        tweets = newarr
    return tweets


def get_current_tweet():
    table = gettable()
    resp = table.get_item(Key={'id': 1})
    return resp['Item']


def update_dynamo(lines, idx, sid=None):
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
    except TweepError:
        sys.exit(TweepError)
    return status.id


def fix_current_tweet(current_tweet):
    if not 'idx' in current_tweet:
        current_tweet['idx'] = len(current_tweet['tweet'])
    else:
        current_tweet['idx'] = int(current_tweet['idx'])
    if not 'sid' in current_tweet:
        current_tweet['sid'] = nosid
    if not 'timelastsent' in current_tweet:
        current_tweet['timelastsent'] = time.time() - 10 * 60
    else:
        current_tweet['timelastsent'] = float(current_tweet['timelastsent'])
    return current_tweet


def check_paragraph(key):
    try:
        files = getfiles()
        p = getnext(key, files)
    except KeyError:
        print('wah wah wah')
        print('key bad')
        return False
    return True


def set_paragraph(key):
    good = check_paragraph(key)
    if good:
        updatekey(key)
        update_dynamo([], 1000, 'nosid')


def main(nowait=False):
    current_tweet = fix_current_tweet(get_current_tweet())

    if current_tweet['idx'] + 1 < len(current_tweet['tweet']):
        content = current_tweet['tweet']
        idx = current_tweet['idx']
        sid = current_tweet['sid']
        sid = tweet(content[idx], sid)
        update_dynamo(content, idx+1, sid)
    elif nowait or time.time() - current_tweet['timelastsent'] >= TIME_BETWEEN_TWEETS:
        key = getkey()
        files = getfiles()
        content = getnext(key, files)
        content = splittweet(content)
        idx = 0
        sid = tweet(content[idx])
        key = incrementkey(key, files)
        updatekey(key)
        update_dynamo(content, idx+1, sid)

    current_tweet = fix_current_tweet(get_current_tweet())
    return current_tweet


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
