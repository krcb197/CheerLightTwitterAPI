"""
This module implements a stand alone application which does the following:

#. Subscribes to an Cornhole MQTT Broker
#. When a update MQTT message occurs for example a game is completed it will tweet out a result
"""
import uuid
from datetime import datetime
import os
import argparse
import logging.config
import re
from dataclasses import dataclass
from typing import Optional

import paho.mqtt.client as mqtt

from cheer_lights_twitter_api import CheerLightTwitterAPI, TwitterAPIVersion, CheerLightColours

file_path = os.path.dirname(__file__)

@dataclass
class HoleState:
    state: bool
    colour: CheerLightColours

class CornHoleTweeter(CheerLightTwitterAPI):
    """
    Main Class

    Args:
        user_template_dir (str): Path to a directory where user-defined jinja template overrides are stored.
        user_template_context (dict): Additional context variables to load into the template namespace.

    """
    _DEFAULT_MQTT_SERVER = 'localhost'
    _DEFAULT_MQTT_SERVER_PORT = 1883

    def __init__(self, **kwargs):

        self.__logger = logging.getLogger(__name__ + '.CornHoleTweeter')

        # initialise the mqtt part of the class
        self.__my_uuid = uuid.uuid4()
        self.__mqtt_client = mqtt.Client(str(self.__my_uuid)+'_cornhole_tweeter')

        mqtt_server = kwargs.pop('mqtt_server', self._DEFAULT_MQTT_SERVER)
        if not isinstance(mqtt_server, str):
            raise TypeError(f'mqtt_server should be of type bool, got {type(mqtt_server)}')
        self.__mqtt_host = mqtt_server

        mqtt_port = kwargs.pop('mqtt_port', self._DEFAULT_MQTT_SERVER_PORT)
        if not isinstance(mqtt_port, int):
            raise TypeError(f'mqtt_server should be of type bool, got {type(mqtt_server)}')
        self.__mqtt_port = mqtt_port

        # initialise the tweeting part of the class
        if 'user_template_dir' not in kwargs:
            kwargs['user_template_dir'] = os.path.join(file_path, 'cornhole_templates')
        super().__init__(**kwargs)

        self.hole_state = [HoleState(state=False, colour=CheerLightColours.RED) for x in range(6)]

        self.__next_score_tweet_colour: Optional[CheerLightColours] = None
        self.__current_username: str = ''

    def mqtt_connect(self):
        self.__mqtt_client.connect(host=self.__mqtt_host,
                                   port=self.__mqtt_port)
        self.__mqtt_client.on_message = self.on_message  # attach function to callback
        self.__mqtt_client.subscribe("$SYS/broker/uptime")
        self.__mqtt_client.subscribe("cornhole/endgame")
        for hole_id in range(6):
            self.__mqtt_client.subscribe(f'holes/{hole_id:d}/hit')
            self.__mqtt_client.subscribe(f'holes/{hole_id:d}/colour')
            self.__mqtt_client.subscribe(f'holes/{hole_id:d}/state')
            self.__mqtt_client.subscribe(f'game/username')
            self.__mqtt_client.subscribe(f'game/current_score')
            self.__mqtt_client.subscribe(f'game/end_score')

        self.__mqtt_client.loop_start()

    def mqtt_disconnect(self):
        self.__mqtt_client.loop_stop(force=True)

    def connect(self):
        self.mqtt_connect()
        super().connect()

    def disconnect(self):
        self.mqtt_disconnect()
        super().disconnect()

    def on_message(self, client, userdata, message):
        now = datetime.now()
        message_payload = message.payload.decode('utf-8')

        topic_match = re.match(r'holes/(\d+)/state', message.topic)
        if topic_match is not None:
            hole_id = int(topic_match.groups()[0])

            message_payload = message.payload.decode('utf-8')

            if hole_id in range(6):
                if message_payload == 'on':
                    self.hole_state[hole_id].state == True
                    self.__logger.debug(f'message recieved {hole_id:d} turned on')
                elif message_payload == 'off':
                    self.hole_state[hole_id].state == False
                    self.__logger.debug(f'message recieved {hole_id:d} turned off')
                else:
                    self.__logger.error(f'unable to decode mqtt {message.topic=:s}, {message_payload=}')
            else:
                self.__logger.error(f'unable to decode mqtt {message.topic=:s}, hole_id out of range')

            return None

        topic_match = re.match(r'holes/(\d+)/colour', message.topic)
        if topic_match is not None:
            hole_id = int(topic_match.groups()[0])

            message_payload = message.payload.decode('utf-8')

            if hole_id in range(6):
                self.hole_state[hole_id].colour = CheerLightColours[message_payload.upper()]
                self.__logger.debug(f'message recieved {hole_id:d} colour set: {self.hole_state[hole_id].colour.name:s}')
            else:
                self.__logger.error(f'unable to decode mqtt {message.topic=:s}, hole_id out of range')

            return None

        topic_match = re.match(r'holes/(\d+)/hit', message.topic)
        if topic_match is not None:
            hole_id = int(topic_match.groups()[0])

            message_payload = message.payload.decode('utf-8')

            if hole_id in range(6):
                if message_payload == 'valid':
                    self.__next_score_tweet_colour = self.hole_state[hole_id].colour
                elif message_payload == 'invalid':
                    pass
                else:
                    self.__logger.error(f'unable to decode mqtt {message.topic=:s}, {message_payload=}')
            else:
                self.__logger.error(f'unable to decode mqtt {message.topic=:s}, hole_id out of range')

            return None

        topic_match = re.match(r'game/current_score', message.topic)
        if topic_match is not None:

            message_payload = message.payload.decode('utf-8')

            if self.__next_score_tweet_colour is not None:
                self.hit_tweet(colour=self.__next_score_tweet_colour, score=int(message_payload))
                # clear the next tweet colour
                self.__next_score_tweet_colour = None

            return None

        topic_match = re.match(r'game/end_score', message.topic)
        if topic_match is not None:

            message_payload = message.payload.decode('utf-8')

            self.endgame_tweet(score=int(message_payload))

            return None

        topic_match = re.match(r'game/username', message.topic)
        if topic_match is not None:
            message_payload = message.payload.decode('utf-8')

            self.__logger.info(f'mqtt username update {message_payload}')
            self.__current_username = message_payload

            return None

        if message.topic == '$SYS/broker/uptime':
            # decode the message
            decoded_re = re.match(r'(\d+) seconds', message_payload)

            if decoded_re is None:
                self.__logger.error(f'unable to decode mqtt topic: cornhole/endgame, {message_payload=}')
            else:
                mqtt_broker_uptime = int(decoded_re.groups()[0])
                self.__logger.debug(f'received an mqtt {message.topic=}, {message_payload=} : decoded {mqtt_broker_uptime=} secs')

            return None

        self.__logger.error(f'received an unexpected mqtt {message.topic=}')

    def endgame_tweet(self, score) -> Optional[int]:
        """
        Send a tweet based on a Jinja template

        Args:
            score (int) : user score for the game
        Returns:
            The tweet sent out
        """
        # if the payload is None then build off the template
        tweet_content = self.template_payload(jinja_template='end_game.jinja',
                                              jinja_context={'current_score':score, 'user_name': self.__current_username})

        self.__logger.info(f'Built Tweet: {tweet_content}')

        return self.tweet(payload=tweet_content)

    def hit_tweet(self, score: int, colour: CheerLightColours) -> Optional[int]:
        """
        Send a tweet based on a Jinja template

        Args:
            score (int) : user score for the game
        Returns:
            The tweet sent out
        """
        # if the payload is None then build off the template
        tweet_content = self.colour_template_payload(colour=colour,
                                                     jinja_context={'current_score': score,
                                                                    'user_name': self.__current_username})

        self.__logger.info(f'Built Tweet: {tweet_content}')

        return self.tweet(payload=tweet_content)

# set up the command line arguments for calling the application
parser = argparse.ArgumentParser(description='Python Code to generate a Cornhole Tweet based on MQTT message',
                                     epilog='See: https://github.com/krcb197/CheerLightTwitterAPI '
                                            'for more details')
parser.add_argument('--mqtt_server', '-a', dest='mqtt_server', type=str, default='localhost',
                    help='address for the MQTT server')
parser.add_argument('--mqtt_port', '-p', dest='mqtt_port', type=int, default=1884,
                    help='port for the MQTT server')
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true',
                    help='All the logging information will be shown in the console')
parser.add_argument('--suppress_tweeting', '-s', dest='suppress_tweeting', action='store_true',
                    help='Makes the connection to twitter but will suppress any update status, '
                         'this is useful for testing')
parser.add_argument('--suppress_connection', '-c', dest='suppress_connection', action='store_true',
                    help='Does not connect to the twitter API, this is useful for testing')
parser.add_argument('--generate_access', '-g', dest='generate_access', action='store_true',
                    help='generate the user access token via a web confirmation')
#parser.add_argument('--destroy_tweet', '-d', dest='destroy_tweet', action='store_true',
#                    help='destroy (delete) the tweet created which is useful in testing')
parser.add_argument('--twitter_api_version', type=str, default='V1',
                    choices=[choice.name for choice in TwitterAPIVersion])

if __name__ == "__main__":

    # parse the command line args
    command_args = parser.parse_args()

    # set up the logging configuration
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
                    'level': 'DEBUG',
                    'propagate': False
                },
                '__main__': {  # if __name__ == '__main__'
                    'handlers': ['default'],
                    'level': 'DEBUG',
                    'propagate': False
                },
            }
        }
        logging.config.dictConfig(LOGGING_CONFIG)

    corn_hole_tweeter = CornHoleTweeter(mqtt_port=command_args.mqtt_port,
                                        mqtt_server=command_args.mqtt_server,
                                        key_path=file_path,
                                        suppress_tweeting=command_args.suppress_tweeting,
                                        suppress_connection=command_args.suppress_connection,
                                        twitter_api_version=TwitterAPIVersion[command_args.twitter_api_version])
    corn_hole_tweeter.connect()