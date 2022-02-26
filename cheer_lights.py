"""
module to demostrate the cheer_lights_twitter_api and provide command line access to it
"""
import argparse

import logging.config

import os

import time

from cheer_lights_twitter_api import CheerLightTwitterAPI
from cheer_lights_twitter_api import CheerLightColours

file_path = os.path.dirname(__file__)

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
parser.add_argument('--destroy_tweet', '-d', dest='destroy_tweet', action='store_true',
                    help='destroy (delete) the tweet created which is useful in testing')

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

    cheer_lights = CheerLightTwitterAPI(key_path=file_path,
                                        suppress_tweeting=command_args.suppress_tweeting,
                                        suppress_connection=command_args.supress_connection,
                                        generate_access=command_args.generate_access)
    cheer_lights.connect()
    tweet_sent = cheer_lights.colour_template_tweet(CheerLightColours[command_args.colour.upper()])

    if (command_args.supress_connection is True) or (command_args.suppress_tweeting is True):
        pass
    else:
        if tweet_sent is None:
            raise RuntimeError('Tweet failed to send')

        if (command_args.destroy_tweet is True) and (command_args.suppress_tweeting is False):
            time.sleep(10)
            cheer_lights.destroy_tweet(tweet_id=tweet_sent.id)
