# The Letters of John and Abigail Twitterbot

This bot runs in AWS lambda, using AWS dynamodb, at regular 1 minute intervals,
tweeting lines from text files scraped with `requests` and `BeautifulSoup4` from
NARA's The Adams Papers and hosted at
[johnandabigail.netlify.app](https://johnandabigail.netlify.app).

The text files can be found in https://github.com/malan88/lettersofjohnandabigail
