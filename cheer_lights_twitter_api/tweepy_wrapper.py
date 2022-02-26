"""
Module to simply the access to Tweepy providing the connectivity, including key management and send a tweet

This also abstracts whether you are using the V1 or V2 Twitter APIs
"""

import logging
import logging.config
from typing import Optional, List
import os
import json
from dataclasses import dataclass
from enum import Enum, auto

import tweepy

@dataclass
class _TwitterAPIKeys:
    """
    Class for holding Twitter API Keys
    """
    consumer_key: str
    consumer_secret: str
    access_token: Optional[str] = None
    access_secret: Optional[str] = None

class TwitterAPIVersion(Enum):
    """
    Version of the Twitter API to use
    """
    V2 = auto()
    V1 = auto()

@dataclass
class Tweet:
    """
    Simplified tweet record to harmonise the V1 and V2 API responses
    """
    tweet_id : int
    text : str

class TweepyWrapper:
    """
    Class to simply the usage of the Tweepy API

    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self,
                 **kwargs):

        self.__logger = logging.getLogger(__name__ + '.TweepyWrapper')

        if 'key_path' not in kwargs:
            raise ValueError('key path must be in the arguments')
        self.__key_path = kwargs.pop('key_path')

        suppress_tweeting = kwargs.pop('suppress_tweeting', False)
        if not isinstance(suppress_tweeting, bool):
            raise TypeError(f'suppress_tweeting should be of type bool, got {type(suppress_tweeting)}')
        self.__suppress_tweeting = suppress_tweeting

        suppress_connection = kwargs.pop('suppress_connection', False)
        if not isinstance(suppress_connection, bool):
            raise TypeError(f'suppress_connection should be of type bool, got {type(suppress_connection)}')
        self.__suppress_connection = suppress_connection

        generate_access = kwargs.pop('generate_access', False)
        if not isinstance(generate_access, bool):
            raise TypeError(f'generate_access should be of type bool, got {type(generate_access)}')
        self.__generate_access_token = generate_access

        api_version = kwargs.pop('twitter_api_version', TwitterAPIVersion.V1)
        if not isinstance(api_version, TwitterAPIVersion):
            raise TypeError(f'api_Version should be of type TwitterAPIVersion, got {type(api_version)}')
        self.__api_version = api_version

        if self.__api_version is TwitterAPIVersion.V1:
            self.__twitter_api: Optional[tweepy.API] = None
        elif self.__api_version is TwitterAPIVersion.V2:
            self.__twitter_client: Optional[tweepy.API] = None
        else:
            raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')

        if len(kwargs) > 0:
            for key, value in kwargs.items():
                self.__logger.error(f'unhandled kwarg {key}, {value}')
            raise RuntimeError('Unhandled object parameters')

        self.__user_id: Optional[int] = None

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

        # whilst reasonable effort must be taken to reduce the branchs, in this case we don't want to expose the keys
        # outside this method so it has to be accepted
        # pylint: disable=too-many-branches

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

            if self.__api_version is TwitterAPIVersion.V1:
                auth.set_access_token(key=twitter_keys.access_token,
                                      secret=twitter_keys.access_secret)

                self.__twitter_api = tweepy.API(auth)
            elif self.__api_version is TwitterAPIVersion.V2:
                self.__twitter_client = tweepy.Client(consumer_key=twitter_keys.consumer_key,
                                                      consumer_secret=twitter_keys.consumer_secret,
                                                      access_token=twitter_keys.access_token,
                                                      access_token_secret=twitter_keys.access_secret)
            else:
                raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')

            self._connect_verify()

    def _connect_verify(self):

        if self.__api_version is TwitterAPIVersion.V1:
            user = self.__twitter_api.verify_credentials()
            self.__logger.info(f'Twitter API access confirmed for {user.name} (@{user.screen_name})')
            self.__user_id = user.id
        elif self.__api_version is TwitterAPIVersion.V2:
            user = self.__twitter_client.get_me()
            self.__logger.info(f'Twitter API access confirmed for {user.data.name} (@{user.data.username})')
            self.__user_id = int(user.data['id'])
        else:
            raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')

    def disconnect(self) -> None:
        """
        Disconnect from the Twitter API
        """
        self.__logger.info('disconnecting from twitter with environmental variable credentials')
        if self.__api_version is TwitterAPIVersion.V1:
            self.__twitter_api = None
        elif self.__api_version is TwitterAPIVersion.V2:
            self.__twitter_client = None
        else:
            raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')

        self.__user_id = None

    def __enter__(self):
        self.connect()
        return self

    def user_tweets(self, count) -> List[Tweet]:
        """
        retrieve the text of the last tweet sent, this is useful for doing a round trip test
        """
        tweets = []
        if self.__api_version is TwitterAPIVersion.V1:
            if self.__twitter_api is None:
                raise RuntimeError('Not connected to the twitter API')
            twitter_response = self.__twitter_api.user_timeline(count=count)
            for tweet in twitter_response:
                tweets.append(Tweet(tweet_id=tweet.id, text=tweet.text))
        elif self.__api_version is TwitterAPIVersion.V2:
            if self.__twitter_client is None:
                raise RuntimeError('Not connected to the twitter API')
            twitter_response = self.__twitter_client.get_users_tweets(id=self.__user_id, max_results=count,
                                                                      user_auth =True)
            for tweet in twitter_response.data:
                tweets.append(Tweet(tweet_id=int(tweet['id']), text=tweet['text']))
        else:
            raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')

        return tweets

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def tweet(self, payload: str) -> Optional[int]:
        """
        Send a tweet with the payload provided
        :param payload: string to tweet
        :type payload: str
        :return: id of the tweet sent
        :rtype: int
        """
        if self.__suppress_connection is True:
            self.__logger.warning('Tweet was suppressed and not sent')
            tweet_id = None
        else:
            if self.__suppress_tweeting is False:
                if self.__api_version is TwitterAPIVersion.V1:
                    if self.__twitter_api is None:
                        raise RuntimeError('Not connected to the twitter API')
                    tweet = self.__twitter_api.update_status(payload)
                    tweet_id = tweet.id
                    self.__logger.info(f'Tweet Sent id={tweet_id:d}')
                elif self.__api_version is TwitterAPIVersion.V2:
                    if self.__twitter_client is None:
                        raise RuntimeError('Not connected to the twitter API')
                    tweet = self.__twitter_client.create_tweet(text=payload)
                    tweet_id = int(tweet.data['id'])
                    self.__logger.info(f'Tweet Sent id={tweet_id:d}')
                else:
                    raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')
            else:
                self.__logger.warning('Tweet was suppressed and not sent')
                tweet_id = None

        return tweet_id

    def destroy_tweet(self, tweet_id: int) -> None:
        """
        removes a tweet

        """
        if self.__api_version is TwitterAPIVersion.V1:
            if self.__twitter_api is None:
                raise RuntimeError('Not connected to the twitter API')
            tweet = self.__twitter_api.destroy_status(tweet_id)
            if tweet.id != tweet_id:
                raise RuntimeError('Tweet Failed to delete')
            self.__logger.info(f'Tweet Deleted {tweet.id}')
        elif self.__api_version is TwitterAPIVersion.V2:
            if self.__twitter_client is None:
                raise RuntimeError('Not connected to the twitter API')
            response = self.__twitter_client.delete_tweet(tweet_id)
            if response.data['deleted'] is not True:
                raise RuntimeError('Tweet Failed to delete')
            self.__logger.info(f'Tweet Deleted={tweet_id}')
        else:
            raise RuntimeError(f'Unhandled Twitter API version {self.__api_version.name}')
