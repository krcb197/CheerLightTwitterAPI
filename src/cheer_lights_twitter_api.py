"""
module to provide an API for making cheerlights tweets
"""
import argparse
from enum import IntEnum
import logging
import logging.config
from typing import Optional, Union
import os
import json

import tweepy
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
        if os.path.exists('twitter_credentials.json'):

            self.__logger.info('connecting to twitter with file credentials')

            with open("twitter_credentials.json", "r", encoding='utf-8') as file:
                creds = json.load(file)

            twitter_consumer_key = creds['CONSUMER_KEY']
            twitter_consumer_secret = creds['CONSUMER_SECRET']
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

        auth = tweepy.OAuthHandler(consumer_key=twitter_consumer_key,
                                   consumer_secret=twitter_consumer_secret)
        auth.set_access_token(key=twitter_access_token,
                              secret=twitter_access_secret)

        self.__twitter_api = tweepy.API(auth)

    def disconnect(self) -> None:
        """
        Disconnect from the Twitter API
        """
        self.__twitter_api = None

    def __enter__(self):
        self.connect()
        return self

    @property
    def __screen_name(self) -> str:
        return self.__twitter_api.get_settings()['screen_name']  # type: ignore

    @property
    def last_tweet_text(self) -> str:
        """
        retrieve the text of the last tweet sent, this is useful for doing a round trip test
        """
        tweet = self.__twitter_api.user_timeline(screen_name=self.__screen_name, # type: ignore
                                                 count=1) # type: ignore
        return tweet[0].text # type: ignore

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

    def tweet_payload(self, colour: Union[CheerLightColours, str]) -> str:
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
        template = self.jj_env.get_template("tweet.jinja")

        tweet_content = template.render(context)

        return tweet_content

    def tweet(self, colour: Union[CheerLightColours, str]) -> None:
        """

        :param colour: colour to include in the tweet
        :return:
        """

        self.verify_colour(colour)

        tweet_content = self.tweet_payload(colour)

        self.__logger.info('Built Tweet: {tweet_content}')

        self.send_tweet(payload=tweet_content)

    def send_tweet(self, payload: str) -> None:
        """
        Send a tweet with the payload provided
        :param payload: string to tweet
        :type payload: str
        """
        if self.__twitter_api is None:
            raise RuntimeError('Not connected to the twitter API')

        self.__twitter_api.update_status(payload)

        self.__logger.info('Tweet Sent')


parser = argparse.ArgumentParser(description='Python Code to generate a CheerLights Tweet',
                                 epilog='See: https://github.com/krcb197/CheerLightTwitterAPI '
                                        'for more details')
parser.add_argument('colour', type=str,
                    choices=[choice.name.lower() for choice in CheerLightColours])
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true')

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

    cheer_lights = CheerLightTwitterAPI()
    cheer_lights.connect()
    cheer_lights.tweet(CheerLightColours[command_args.colour.upper()])
