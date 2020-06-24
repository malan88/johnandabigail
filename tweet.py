import os
import re
import textwrap


def getkey():
    """Get the key as a string"""
    with open('key.txt', 'rt') as fin:
        key = fin.read()
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
    key = incrementkey(key, files)
    with open('key.txt', 'wt') as fout:
        fout.write(key)


def splitkey(key):
    """Split the key, return it as two ints."""
    key = [int(el) for el in key.split(':')]
    return key[0], key[1]


def getparagraphs(f):
    """Get all the paragraphs as a list without empty strings."""
    with open('all/' + f, 'rt') as fin:
        paragraphs = fin.readlines()
    return list(filter(None, map(str.strip, paragraphs)))


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


def tweet():
    key = getkey()
    files = os.listdir('all')
    files.sort()
    next = getnext(key, files)
    updatekey(key, files)
    next = splittweet(next)
    print(next, len(next))


if __name__ == "__main__":
    tweet()
