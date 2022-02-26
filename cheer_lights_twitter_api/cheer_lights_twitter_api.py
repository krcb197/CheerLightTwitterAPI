"""
module to provide an API for making cheerlights tweets
"""

from enum import IntEnum

import logging
import logging.config

from typing import Optional, Union, Dict, Any
import os

from .tweepy_jinja_wrapper import TweepyJinjaWrapper
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

class CheerLightTwitterAPI(TweepyJinjaWrapper):
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
                         user_template_dir=user_template_dir,
                         user_template_context=user_template_context,
                         suppress_tweeting=suppress_tweeting,
                         suppress_connection=suppress_connection,
                         generate_access=generate_access)

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

    def colour_template_payload(self, colour: Union[CheerLightColours, str],
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
        if jinja_context is not None:
            context.update(jinja_context)

        tweet_content = self.template_payload(jinja_context=context)

        return tweet_content

    def colour_template_tweet(self, colour: Union[CheerLightColours, str],
                              jinja_context: Optional[Dict[str, Any]] = None) -> Optional[TweepyStatus]:
        """

        :param colour: colour to include in the tweet
        :param jinja_context: a dictionary containing the jinja context to use with the template
                              this is addition to the provided with the object is initialised and
                              the context generated within the function itself
        :return:
        """
        payload = self.colour_template_payload(colour=colour, jinja_context=jinja_context)

        self.__logger.info(f'tweet prepared: {payload}')

        return super().tweet(payload=payload)
