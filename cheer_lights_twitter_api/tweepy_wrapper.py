"""
Module to simply the access to Tweepy providing the connectivity, including key management and send a tweet

This also abstracts whether you are using the V1 or V2 Twitter APIs
"""

import logging
import logging.config
from typing import Optional
import os
import json
from dataclasses import dataclass

import tweepy
from tweepy.models import Status as TweepyStatus
from tweepy.models import ResultSet as TweepyResultSet

@dataclass
class _TwitterAPIKeys:
    """
    Class for holding Twitter API Keys
    """
    consumer_key: str
    consumer_secret: str
    access_token: Optional[str] = None
    access_secret: Optional[str] = None

class TweepyWrapper:
    """
    Class to simply the usage of the Tweepy API


    """

    def __init__(self,
                 key_path: str,
                 suppress_tweeting: bool = False,
                 suppress_connection: bool = False,
                 generate_access: bool = False):

        if not isinstance(suppress_tweeting, bool):
            raise TypeError(f'suppress_tweeting should be of type bool, got {type(suppress_tweeting)}')

        self.__suppress_tweeting = suppress_tweeting

        if not isinstance(suppress_connection, bool):
            raise TypeError(f'suppress_connection should be of type bool, got {type(suppress_connection)}')

        self.__suppress_connection = suppress_connection

        if not isinstance(generate_access, bool):
            raise TypeError(f'generate_access should be of type bool, got {type(generate_access)}')

        self.__generate_access_token = generate_access

        self.__key_path = key_path

        self.__twitter_api: Optional[tweepy.API] = None

        self.__logger = logging.getLogger(__name__ + '.TweepyWrapper')

    @property
    def __consumer_key_fqfn(self) -> str:
        """
        path to the fully qualified consumer key file name
        """
        return os.path.join(self.__key_path, "consumer_twitter_credentials.json")

    @property
    def __access_key_fqfn(self) -> str:
        """
        path to the fully qualified access key file name
        """
        return os.path.join(self.__key_path, "access_twitter_credentials.json")

    def connect(self) -> None:
        """
        Connect to the Twitter API
        """
        def get_keys_from_files(generate_access_token) -> _TwitterAPIKeys:
            with open(self.__consumer_key_fqfn, "r", encoding='utf-8') as file:
                creds = json.load(file)

                twitter_consumer_key = creds['CONSUMER_KEY']
                twitter_consumer_secret = creds['CONSUMER_SECRET']

            if generate_access_token is False:
                # If the access token is not to be generated it must be read from a file
                with open(self.__access_key_fqfn, "r", encoding='utf-8') as file:
                    creds = json.load(file)

                return _TwitterAPIKeys(consumer_key=twitter_consumer_key,
                                       consumer_secret=twitter_consumer_secret,
                                       access_token=creds['ACCESS_TOKEN'],
                                       access_secret=creds['ACCESS_SECRET'])

            return _TwitterAPIKeys(consumer_key=twitter_consumer_key,
                                   consumer_secret=twitter_consumer_secret)

        def get_keys_from_env() -> _TwitterAPIKeys:

            # check for environment variables
            twitter_consumer_key = os.environ.get("TWITTER_API_KEY")
            twitter_consumer_secret = os.environ.get("TWITTER_API_SECRET")
            twitter_access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
            twitter_access_secret = os.environ.get("TWITTER_ACCESS_SECRET")


            if twitter_consumer_key is None:
                raise RuntimeError('Environment Variable: TWITTER_API_KEY missing')

            if twitter_consumer_secret is None:
                raise RuntimeError('Environment Variable: TWITTER_API_SECRET missing')

            if twitter_access_token is None:
                raise RuntimeError('Environment Variable: TWITTER_ACCESS_TOKEN missing')

            if twitter_access_secret is None:
                raise RuntimeError('Environment Variable: TWITTER_ACCESS_SECRET missing')

            return _TwitterAPIKeys(consumer_key=twitter_consumer_key,
                                   consumer_secret=twitter_consumer_secret,
                                   access_token=twitter_access_token,
                                   access_secret=twitter_access_secret)

        if self.__suppress_connection is True:
            self.__logger.warning('connecting to twitter is suppressed')

        else:
            if os.path.exists(self.__consumer_key_fqfn):

                self.__logger.info('connecting to twitter with file credentials')

                twitter_keys = get_keys_from_files(generate_access_token=self.__generate_access_token)

            else:

                if self.__generate_access_token is True:
                    raise RuntimeError('generation of access tokens is not supported with '
                                       'environment variable mode')

                self.__logger.info('connecting to twitter with environmental variable credentials')

                twitter_keys = get_keys_from_env()

            if self.__generate_access_token is True:
                auth = tweepy.OAuthHandler(consumer_key=twitter_keys.consumer_key,
                                                consumer_secret=twitter_keys.consumer_secret,
                                                callback='oob')

                auth_url = auth.get_authorization_url()
                print('Authorization URL: ' + auth_url)

                # ask user to verify the PIN generated in browser
                verifier = input('PIN: ').strip()
                auth.get_access_token(verifier)

                if os.path.exists(self.__access_key_fqfn):
                    confirm = input('overwite access_twitter_credentials.json '
                                    'file [Y/N]').strip().upper()
                    if confirm == 'Y':
                        with open(self.__access_key_fqfn, "w",
                                  encoding='utf-8') as file:
                            json.dump({'ACCESS_TOKEN': auth.access_token,
                                       'ACCESS_SECRET': auth.access_token_secret }, file)

                        twitter_keys.access_token = auth.access_token
                        twitter_keys.access_secret = auth.access_token_secret
                    elif confirm == 'N':
                        print('using the access token but not overwriting the file')

                        twitter_keys.access_token = auth.access_token
                        twitter_keys.access_secret = auth.access_token_secret

                    else:
                        raise RuntimeError('Unhandled choice {confirm}')

            else:
                auth = tweepy.OAuth1UserHandler(consumer_key=twitter_keys.consumer_key,
                                                consumer_secret=twitter_keys.consumer_secret)

            auth.set_access_token(key=twitter_keys.access_token,
                                  secret=twitter_keys.access_secret)

            self.__twitter_api = tweepy.API(auth)

            user = self.__twitter_api.verify_credentials()

            self.__logger.info(f'Twitter API access confirmed for {user.name} (@{user.screen_name})')

    def disconnect(self) -> None:
        """
        Disconnect from the Twitter API
        """
        self.__logger.info('disconnecting from twitter with environmental variable credentials')
        self.__twitter_api = None

    def __enter__(self):
        self.connect()
        return self

    @property
    def last_tweet(self) -> TweepyResultSet:
        """
        retrieve the text of the last tweet sent, this is useful for doing a round trip test
        """
        if self.__twitter_api is None:
            raise RuntimeError('Twitter API not connected')

        tweet = self.__twitter_api.user_timeline(count=1)
        return tweet

    def tweets_since(self, since_id, count) -> TweepyResultSet:
        """
        retrieve the text of the last tweet sent, this is useful for doing a round trip test
        """
        if self.__twitter_api is None:
            raise RuntimeError('Twitter API not connected')

        tweet = self.__twitter_api.user_timeline(since_id=since_id, count=count)
        return tweet

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def tweet(self, payload: str) -> Optional[TweepyStatus]:
        """
        Send a tweet with the payload provided
        :param payload: string to tweet
        :type payload: str
        """
        if self.__suppress_connection is True:
            self.__logger.warning('Tweet was suppressed and not sent')
            tweet = None
        else:
            if self.__twitter_api is None:
                raise RuntimeError('Not connected to the twitter API')

            if self.__suppress_tweeting is False:
                #tweet = self.__twitter_api.create_tweet(text=payload, user_auth=True)
                tweet = self.__twitter_api.update_status(payload)

                self.__logger.info(f'Tweet Sent {tweet.id}')
            else:
                self.__logger.warning('Tweet was suppressed and not sent')
                tweet = None

        return tweet

    def destroy_tweet(self, tweet_id: int) -> TweepyStatus:
        """
        removes a tweet

        """
        if self.__twitter_api is None:
            raise RuntimeError('Not connected to the twitter API')

        tweet = self.__twitter_api.destroy_status(tweet_id)
        self.__logger.info(f'Tweet Deleted {tweet.id}')
        return tweet
