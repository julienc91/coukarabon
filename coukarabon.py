#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Coukarabon
https://github.com/julienc91/coukarabon
"""

import re
import os
import time
import pickle

import twitter
from requests_oauthlib import OAuth1Session


CONSUMER_KEY = "XXX"
CONSUMER_SECRET = "XXX"

REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

TARGET_SCREEN_NAME = "Coukaratcheat"
TARGET_TWEET_REGEX = re.compile(r"^((@\w+\s+)|(\b))*bon\b",
                                re.IGNORECASE)
TARGET_TWEET_ANSWER = "@{} Bon.".format(TARGET_SCREEN_NAME)

WORKING_DIRECTORY = os.path.join(os.path.expanduser("~"),
                                 ".local/share/coukarabon")
TOKEN_FILE = os.path.join(WORKING_DIRECTORY, "token")
LAST_TWEET_FILE = os.path.join(WORKING_DIRECTORY, "last_tweet")


def get_oauth_access_token():

    """Oauth authentication"""

    # if the toen file exists, t    ry to load the tokens from it
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token_file:
            try:
                return pickle.load(token_file)
            except (pickle.UnpicklingError, EOFError):
                # nothing to worry about, we can ask for a new token
                pass

    client = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET)
    client.fetch_request_token(REQUEST_TOKEN_URL)

    print("Go to the following link in your browser:\n"
          "{}\n".format(client.authorization_url(AUTHORIZE_URL)))

    oauth_verifier = input('What is the PIN? ')

    access_tokens = client.fetch_access_token(ACCESS_TOKEN_URL,
                                              verifier=oauth_verifier)
    token = access_tokens['oauth_token']
    secret = access_tokens['oauth_token_secret']

    # store the token so that we won't need the user to authenticate next time
    with open(TOKEN_FILE, 'wb') as token_file:
        pickle.dump((token, secret), token_file)

    return token, secret


def api_authentication(token, secret):

    """Instanciate an API client"""

    api = twitter.Twitter(auth=twitter.OAuth(token, secret,
                                             CONSUMER_KEY, CONSUMER_SECRET))
    if not api:
        print("Authentication failed, try running the script one more time")

        # delete data from the configuration file to force a new
        # authentication next time
        os.remove(TOKEN_FILE)
        return None

    return api


def get_tweets_to_answer_to(api, last_tweet_id=0):

    """Get tweets which will be targeted by the bot"""

    parameters = {"screen_name": TARGET_SCREEN_NAME,
                  "include_rts": False,
                  "count": 200}
    if last_tweet_id > 0:
        parameters["since_id"] = last_tweet_id

    last_tweets = api.statuses.user_timeline(**parameters)
    tweets_to_answer_to = sorted([tweet for tweet in last_tweets
                                  if TARGET_TWEET_REGEX.match(tweet["text"])],
                                 key=lambda t: t["id"])

    if last_tweets and not tweets_to_answer_to:
        # update the last tweet id so that we wont consider the same tweets
        # again next time
        update_last_tweet_id(sorted(last_tweets, key=lambda t: t["id"])[-1]["id"])

    return tweets_to_answer_to


def answer_to_tweets(api, tweets):

    """Post an answer to the given tweets"""

    try:
        last_tweet_id = 0
        for tweet in tweets:
            print("Sending an answer to tweet {}: '{}'".format(tweet["id"],
                                                               tweet["text"]))
            api.statuses.update(status=TARGET_TWEET_ANSWER,
                                in_reply_to_status_id=tweet["id"])
            last_tweet_id = tweet["id"]
            time.sleep(1)  # do not exceed Twitter limits
    finally:
        update_last_tweet_id(last_tweet_id)


def get_last_tweet_id():

    """Retrieve the id of the last tweet we answered to"""

    if not os.path.exists(LAST_TWEET_FILE):
        return 0

    try:
        with open(LAST_TWEET_FILE, 'rb') as last_tweet_file:
            return pickle.load(last_tweet_file)
    except pickle.UnpicklingError:
        return 0


def update_last_tweet_id(last_tweet_id):

    """Update the id of the last tweet the bot considered"""

    if last_tweet_id:
        with open(LAST_TWEET_FILE, 'wb') as last_tweet_file:
            pickle.dump(last_tweet_id, last_tweet_file)


def main():

    """Start here"""

    if not os.path.exists(WORKING_DIRECTORY):
        os.makedirs(WORKING_DIRECTORY)

    token, secret = get_oauth_access_token()
    api = api_authentication(token, secret)
    if not api:
        raise RuntimeError("Could not instanciate an API client")

    last_tweet_id = get_last_tweet_id()
    tweets = get_tweets_to_answer_to(api, last_tweet_id)
    answer_to_tweets(api, tweets)


if __name__ == "__main__":
    main()
