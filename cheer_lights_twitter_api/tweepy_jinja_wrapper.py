"""
Module to extend the tweepy wrapper to support jinja templating
"""

import logging
import logging.config

from typing import Optional, Dict, Any
import os

import jinja2 as jj

from .tweepy_wrapper import TweepyWrapper

file_path = os.path.dirname(__file__)


class TweepyJinjaWrapper(TweepyWrapper):
    """
    Class to sent a tweet to the Cheerlights server

    :param user_template_dir: Path to a directory where user-defined template overrides are stored.
    :type user_template_dir: str
    :param user_template_context: Additional context variables to load into the template namespace.
    :type user_template_context: type
    """

    def __init__(self,
                 **kwargs):

        user_template_context = kwargs.pop('user_template_context', None)
        user_template_dir = kwargs.pop('user_template_dir', None)
        super().__init__(**kwargs)

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

        self.__jj_env = jj.Environment(
            loader=loader,
            undefined=jj.StrictUndefined
        )

        self.__logger = logging.getLogger(__name__ + '.CheerLightTwitterAPI')

    def template_payload(self, jinja_context: Optional[Dict[str, Any]] = None) -> str:
        """
        String to be tweeted out based on the colour
        :param jinja_context: a dictionary containing the jinja context to use with the template
                              this is addition to the provided with the object is initialised and
                              the context generated within the function itself
        :return: tweet payload
        """

        context = {}
        context.update(self.__user_template_context)
        if jinja_context is not None:
            context.update(jinja_context)
        template = self.__jj_env.get_template("tweet.jinja")

        tweet_content = template.render(context)

        return tweet_content

    def template_tweet(self, jinja_context: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Send a tweet based on a Jinja template


        :param jinja_context: a dictionary containing the jinja context to use with the template
                              this is addition to the provided with the object is initialised and
                              the context generated within the function itself
        :return:
        """
        # if the payload is None then build off the template
        tweet_content = self.template_payload(jinja_context)

        self.__logger.info(f'Built Tweet: {tweet_content}')

        return self.tweet(payload=tweet_content)
