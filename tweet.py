import re
import textwrap
import boto3
import time
import urllib3
import json
import argparse

TABLE='adams-family'
LETTERS='https://johnandabigail.netlify.app/'


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


def updatekey(key, files):
    table = gettable()
    key = incrementkey(key, files)
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


def dynamo_tweet(tweet):
    table = gettable()
    table.update_item(
        Key={'id': 1},
        UpdateExpression="set tweet=:k",
        ExpressionAttributeValues={
            ':k': tweet
        }
    )


def tweet(test=False, dynamodb=False):
    key = getkey()
    files = getfiles()
    next = getnext(key, files)
    updatekey(key, files)
    next = splittweet(next)
    if dynamodb:
        dynamo_tweet(next)
        print("Tweet away, captain.")
    elif test:
        for t in next:
            print(t)
            print("Tweet away, captain.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--loop", help="Loop every 10 minutes to tweet",
                        action="store_true")
    parser.add_argument("-t", "--test",
                        help="Just test tweet by printing to stdout",
                        action="store_true")
    parser.add_argument("-d", "--dynamodb", help="Update dynamodb for testing",
                        action="store_true")
    args = parser.parse_args()
    if args.loop:
        while True:
            tweet(args.test, args.dynamodb)
    else:
        tweet(args.test, args.dynamodb)
