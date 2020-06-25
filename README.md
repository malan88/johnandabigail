# The Letters of John and Abigail Twitterbot

This bot runs in AWS lambda, using AWS dynamodb, at regular 1 minute intervals,
tweeting lines from text files scraped with `requests` and `BeautifulSoup4` from
NARA's The Adams Papers and hosted at
[johnandabigail.netlify.app](https://johnandabigail.netlify.app).

The text files can be found in the
[https://github.com/malan88/lettersofjohnandabigail](lettersofjohnandabigail)
repo.

Most of the files in this repo are just for packaging tweepy. I have to figure
out how to make this a cleaner repo.

My files are the Makefile, the __init__.py, lambda.zip, lambda_function.py,
list.json, and tweet.py.

You can see the bot in action at
[@john_and_abbie](https://twitter.com/john_and_abbie).
