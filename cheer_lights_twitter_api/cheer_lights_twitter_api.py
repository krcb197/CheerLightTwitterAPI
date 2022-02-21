"""
module to provide an API for making cheerlights tweets
"""

from enum import IntEnum

import logging
import logging.config

from typing import Optional, Union, Dict, Any
import os

import jinja2 as jj

from .tweepy_wrapper import TweepyWrapper
from .tweepy_wrapper import TweepyStatus

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

class CheerLightTwitterAPI(TweepyWrapper):
    """
    Class to sent a tweet to the Cheerlights server

    :param user_template_dir: Path to a directory where user-defined template overrides are stored.
    :type user_template_dir: str
    :param user_template_context: Additional context variables to load into the template namespace.
    :type user_template_context: type
    """

    def __init__(self,
                 key_path: str,
                 user_template_dir: Optional[str] = None,
                 user_template_context: Optional[Dict[str, Any]] = None,
                 suppress_tweeting: bool = False,
                 suppress_connection: bool = False,
                 generate_access: bool = False):

        super().__init__(key_path=key_path,
                         suppress_tweeting=suppress_tweeting,
                         suppress_connection=suppress_connection,
                         generate_access=generate_access)

        if user_template_context is None:
            self.__user_template_context = {}
        else:
            self.__user_template_context = user_template_context

        if user_template_dir:
            loader = jj.ChoiceLoader([
                jj.FileSystemLoader(user_template_dir),
                jj.FileSystemLoader(os.path.join(file_path, "../cheer_lights_twitter_api/templates")),
                jj.PrefixLoader({'user': jj.FileSystemLoader(user_template_dir),
                                 'base': jj.FileSystemLoader(os.path.join(file_path,
                                                                          "../cheer_lights_twitter_api/templates"))
                                 },
                                delimiter=":")
            ])
        else:
            loader = jj.ChoiceLoader([
                jj.FileSystemLoader(os.path.join(file_path, "../cheer_lights_twitter_api/templates")),
                jj.PrefixLoader({'base': jj.FileSystemLoader(os.path.join(file_path,
                                                                          "../cheer_lights_twitter_api/templates"))},
                                delimiter=":")])

        self.jj_env = jj.Environment(
            loader=loader,
            undefined=jj.StrictUndefined
        )

        self.__logger = logging.getLogger(__name__ + '.CheerLightTwitterAPI')

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
        :param jinja_context: a dictionary containing the jinja context to use with the template
                              this is addition to the provided with the object is initialised and
                              the context generated within the function itself
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
        :param jinja_context: a dictionary containing the jinja context to use with the template
                              this is addition to the provided with the object is initialised and
                              the context generated within the function itself
        :return:
        """

        self.verify_colour(colour)

        tweet_content = self.tweet_payload(colour, jinja_context)

        self.__logger.info(f'Built Tweet: {tweet_content}')

        return super().tweet(payload=tweet_content)
