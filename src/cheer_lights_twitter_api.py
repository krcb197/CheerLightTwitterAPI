"""
module to provide an API for making cheerlights tweets
"""
import argparse
from enum import IntEnum
import logging
import logging.config
from typing import Optional, Union, Dict, Any
import os
import json

import tweepy
from tweepy.models import Status as TweepyStatus
from tweepy.models import ResultSet as TweepyResultSet
import jinja2 as jj

file_path = os.path.dirname(__file__)

class CheerLightColours(IntEnum):
    """
    colour supported by CheerLight API
    """
    RED = 0xFF0000
    GREEN = 0x008000
    BLUE = 0x0000FF
    CYAN = 0x00FFFF
    WHITE = 0xFFFFFF
    OLDLACE = 0xFDF5E6
    PURPLE = 0x800080
    MAGENTA = 0xFF00FF
    YELLOW = 0xFFFF00
    ORANGE = 0xFFA500
    PINK = 0xFFC0CB

class CheerLightTwitterAPI:
    """
    Class to sent a tweet to the Cheerlights server

    :param user_template_dir: Path to a directory where user-defined template overrides are stored.
    :type user_template_dir: str
    :param user_template_context: Additional context variables to load into the template namespace.
    :type user_template_context: type
    """

    def __init__(self, **kwargs):

        user_template_dir = kwargs.pop("user_template_dir", None)
        self.__user_template_context = kwargs.pop("user_template_context", {})
        self.__supress_tweeting = kwargs.pop("suppress_tweeting", False)
        self.__supress_connection = kwargs.pop("suppress_connection", False)

        if user_template_dir:
            loader = jj.ChoiceLoader([
                jj.FileSystemLoader(user_template_dir),
                jj.FileSystemLoader(os.path.join(file_path, "templates")),
                jj.PrefixLoader({ 'user': jj.FileSystemLoader(user_template_dir),
                                  'base': jj.FileSystemLoader(os.path.join(file_path, "templates"))
                                },
                                delimiter=":")
            ])
        else:
            loader = jj.ChoiceLoader([
                jj.FileSystemLoader(os.path.join(file_path, "templates")),
                jj.PrefixLoader({'base': jj.FileSystemLoader(os.path.join(file_path, "templates"))},
                                delimiter=":")])

        self.jj_env = jj.Environment(
            loader=loader,
            undefined=jj.StrictUndefined
        )

        self.__twitter_api: Optional[tweepy.API] = None

        self.__logger = logging.getLogger(__name__ + '.CheerLightTwitterAPI')

    def connect(self) -> None:
        """
        Connect to the Twitter API
        """
        if self.__supress_connection is True:
            self.__logger.warning('connecting to twitter is supressed')
        else:
            if os.path.exists('consumer_twitter_credentials.json'):

                self.__logger.info('connecting to twitter with file credentials')

                with open("consumer_twitter_credentials.json", "r", encoding='utf-8') as file:
                    creds = json.load(file)

                    twitter_consumer_key = creds['CONSUMER_KEY']
                    twitter_consumer_secret = creds['CONSUMER_SECRET']

                if self.__generate_access_token is False:

                    # If the access token is not to be generated it must be read from a file
                    with open("access_twitter_credentials.json", "r", encoding='utf-8') as file:
                        creds = json.load(file)

                        twitter_access_token = creds['ACCESS_TOKEN']
                        twitter_access_secret = creds['ACCESS_SECRET']

            else:

                self.__logger.info('connecting to twitter with environmental variable credentials')

                # check for enviromental variables
                for var in ['TWITTER_API_KEY', "TWITTER_API_SECRET",
                            "TWITTER_ACCESS_SECRET",
                            "TWITTER_ACCESS_SECRET" ]:
                    if var not in os.environ:
                        self.__logger.error(f'enviroment variable {var} not present')

                twitter_consumer_key = os.environ.get("TWITTER_API_KEY")
                twitter_consumer_secret = os.environ.get("TWITTER_API_SECRET")
                twitter_access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
                twitter_access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

                if self.__generate_access_token is True:
                    raise RuntimeError('generation of access tokens is not supported with '
                                       'environment variable mode')

            if self.__generate_access_token is True:
                auth = tweepy.OAuthHandler(consumer_key=twitter_consumer_key,
                                                consumer_secret=twitter_consumer_secret,
                                                callback='oob')

                auth_url = auth.get_authorization_url()
                print('Authorization URL: ' + auth_url)

                # ask user to verify the PIN generated in broswer
                verifier = input('PIN: ').strip()
                auth.get_access_token(verifier)

                if os.path.exists('access_twitter_credentials.json'):
                    confirm = input('overwite access_twitter_credentials.json '
                                    'file [Y/N]').strip().upper()
                    if confirm == 'Y':
                        with open("access_twitter_credentials.json", "w",
                                  encoding='utf-8') as file:
                            json.dump({'ACCESS_TOKEN': auth.access_token,
                                       'ACCESS_SECRET': auth.access_token_secret }, file)

                        twitter_access_token = auth.access_token
                        twitter_access_secret = auth.access_token_secret
                    elif confirm == 'N':
                        print('using the access token but not overwriting the file')

                        twitter_access_token = auth.access_token
                        twitter_access_secret = auth.access_token_secret

                    else:
                        raise RuntimeError('Unhandled choice {confirm}')

                auth.set_access_token(key=twitter_access_token,
                                      secret=twitter_access_secret)
            else:
                auth = tweepy.OAuth1UserHandler(consumer_key=twitter_consumer_key,
                                                consumer_secret=twitter_consumer_secret)

            auth.set_access_token(key=twitter_access_token,
                                  secret=twitter_access_secret)

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

    @staticmethod
    def verify_colour(colour: Union[CheerLightColours, str]) -> None:
        """
        checks that colour is valid and raises an exception if it in invalid
        :param colour:
        :raises: TypeError, ValueError
        """

        if not isinstance(colour, (CheerLightColours, str)):
            raise TypeError(f'colour should be a str or {type(CheerLightColours)} '
                            f'but got {type(colour)}')

        if isinstance(colour, str):
            if colour.upper() not in CheerLightColours.__members__:
                raise ValueError(f'{colour} is not a legal colour to choose')

    def tweet_payload(self, colour: Union[CheerLightColours, str],
                      jinja_context: Optional[Dict[str, Any]] = None) -> str:
        """
        String to be tweeted out based on the colour
        :param colour: colour
        :return: tweet payload
        """

        self.verify_colour(colour)

        # build message using a jinga template
        if isinstance(colour, str):
            colour_str = colour
        elif isinstance(colour, CheerLightColours):
            colour_str = colour.name.lower()
        else:
            raise RuntimeError('unhandled colour type')

        context = {
            'colour': colour_str
        }
        context.update(self.__user_template_context)
        if jinja_context is not None:
            context.update(jinja_context)
        template = self.jj_env.get_template("tweet.jinja")

        tweet_content = template.render(context)

        return tweet_content

    def tweet(self, colour: Union[CheerLightColours, str],
              jinja_context: Optional[Dict[str, Any]] = None) -> Optional[TweepyStatus]:
        """

        :param colour: colour to include in the tweet
        :return:
        """

        self.verify_colour(colour)

        tweet_content = self.tweet_payload(colour, jinja_context)

        self.__logger.info(f'Built Tweet: {tweet_content}')

        return self.send_tweet(payload=tweet_content)

    def send_tweet(self, payload: str) -> Optional[TweepyStatus]:
        """
        Send a tweet with the payload provided
        :param payload: string to tweet
        :type payload: str
        """
        if self.__supress_connection is True:
            self.__logger.warning('Tweet was suppressed and not sent')
            tweet = None
        else:
            if self.__twitter_api is None:
                raise RuntimeError('Not connected to the twitter API')

            if self.__supress_tweeting is False:
                #tweet = self.__twitter_api.create_tweet(text=payload, user_auth=True)
                tweet = self.__twitter_api.update_status(payload)

                self.__logger.info('Tweet Sent')
            else:
                self.__logger.warning('Tweet was suppressed and not sent')
                tweet = None

        return tweet


parser = argparse.ArgumentParser(description='Python Code to generate a CheerLights Tweet',
                                 epilog='See: https://github.com/krcb197/CheerLightTwitterAPI '
                                        'for more details')
parser.add_argument('colour', type=str,
                    choices=[choice.name.lower() for choice in CheerLightColours])
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true',
                    help='All the logging information will be shown in the console')
parser.add_argument('--suppress_tweeting', '-s', dest='suppress_tweeting', action='store_true',
                    help='Makes the connection to twitter but will suppress any update status, '
                         'this is useful for testing')
parser.add_argument('--supress_connection', '-c', dest='supress_connection', action='store_true',
                    help='Does not connect to the twitter API, this is useful for testing')
parser.add_argument('--generate_access', '-g', dest='generate_access', action='store_true',
                    help='generate the user access token via a web confirmation')

if __name__ == "__main__":

    command_args = parser.parse_args()

    if command_args.verbose:
        LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                },
            },
            'handlers': {
                'default': {
                    'level': 'INFO',
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',  # Default is stderr
                },
            },
            'loggers': {
                '': {  # root logger
                    'handlers': ['default'],
                    'level': 'INFO',
                    'propagate': False
                },
                '__main__': {  # if __name__ == '__main__'
                    'handlers': ['default'],
                    'level': 'INFO',
                    'propagate': False
                },
            }
        }
        logging.config.dictConfig(LOGGING_CONFIG)

    cheer_lights = CheerLightTwitterAPI(suppress_tweeting=command_args.suppress_tweeting,
                                        suppress_connection=command_args.supress_connection,
                                        generate_access=command_args.generate_access)
    cheer_lights.connect()
    tweet_sent = cheer_lights.tweet(CheerLightColours[command_args.colour.upper()])
