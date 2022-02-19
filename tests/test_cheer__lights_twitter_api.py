import os
from typing import Union

from random import randint

import pytest
from pytest_mock import mocker
import sys

from src.cheer_lights_twitter_api import CheerLightTwitterAPI
from src.cheer_lights_twitter_api import CheerLightColours

@pytest.fixture()
def mocked_tweepy(mocker):

    tweepy_api_patch = mocker.patch('src.cheer_lights_twitter_api.tweepy.API')
    tweepy_auth_handler_patch = mocker.patch('src.cheer_lights_twitter_api.tweepy.OAuth1UserHandler')

    yield {'tweepy_api_patch':tweepy_api_patch,
           'tweepy_auth_handler_patch' : tweepy_auth_handler_patch}

def test_tweet_unit_test(mocked_tweepy):
    """
    test that the tweets are made using a mock tweepy
    """

    dut = CheerLightTwitterAPI()
    dut.connect()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.tweet('blue')
    mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_called_once_with('@cheerlights blue')
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.disconnect()

def test_supressed_tweet_unit_test(mocked_tweepy):
    """
    test that the tweets are not made id the suppress_tweeting option is selected
    """
    dut = CheerLightTwitterAPI(suppress_tweeting=True)
    dut.connect()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.tweet('blue')
    mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_not_called()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.disconnect()


def test_tweet_payload():
    """
    test that the tweets are correctly formed with the base template
    """
    dut = CheerLightTwitterAPI()
    # no need to connect to just test the payload generation

    # check a few manually
    payload = dut.tweet_payload(colour=CheerLightColours.RED)
    assert payload == '@cheerlights red'

    payload = dut.tweet_payload(colour=CheerLightColours.BLUE)
    assert payload == '@cheerlights blue'

    payload = dut.tweet_payload(colour=CheerLightColours.RED)
    assert payload == '@cheerlights red'

    payload = dut.tweet_payload(colour='magenta')
    assert payload == '@cheerlights magenta'

    payload = dut.tweet_payload(colour='orange')
    assert payload == '@cheerlights orange'

    # check some bad inputs
    with pytest.raises(TypeError):
        payload = dut.tweet_payload(colour=0xFFFFFF)

    with pytest.raises(ValueError):
        payload = dut.tweet_payload(colour='darkblue')

    # loop through all the colours
    for colour in CheerLightColours:
        payload = dut.tweet_payload(colour=colour)
        assert payload == f'@cheerlights {colour.name.lower()}'

def test_custom_template():
    """
    test overloading the jinja template with a custom template
    """

    file_path = os.path.dirname(__file__)
    custom_templates = os.path.join(file_path, 'custom_template')

    custom_context = {
        'user' : 'Bob'
    }

    dut = CheerLightTwitterAPI(user_template_dir=custom_templates,
                               user_template_context=custom_context)
    # no need to connect to just test the payload generation
    payload = dut.tweet_payload(colour='orange')
    assert payload == '@cheerlights orange from Bob'

@pytest.mark.integration_test
def test_tweet():
    """
    test sending a tweet, we will not actually send a tweet to @cheerlights by overloading the
    tweet payload (which has been tested above)
    """

    class TestCheerLightTwitterAPI(CheerLightTwitterAPI):
        """
        local class with overloaded method
        """

        def __init__(self):
            super().__init__()

            self.last_random_value = 0

        def tweet_payload(self, colour: Union[CheerLightColours, str]) -> str:

            self.last_random_value = randint(0, 2**32)

            self.verify_colour(colour)

            # build message using a jinga template
            if isinstance(colour, str):
                colour_str = colour
            elif isinstance(colour, CheerLightColours):
                colour_str = colour.name.lower()
            else:
                raise RuntimeError('unhandled colour type')

            # twitter API blocks tweets which are duplicate values so add a random value to
            # stop this causing an error
            return f'test tweet {colour_str} with random value {self.last_random_value:d} on ' \
                   f'Python {sys.version_info.major}.{sys.version_info.minor}'


    # test with manual connect disconnect
    dut = TestCheerLightTwitterAPI()

    with pytest.raises(RuntimeError):
        dut.tweet('red')

    dut.connect()
    dut.tweet('blue')
    assert dut.last_tweet_text.startswith(f'test tweet blue with random value '
                                          f'{dut.last_random_value:d}')
    dut.disconnect()

    # test in a context manager
    with TestCheerLightTwitterAPI() as alt_dut:
        alt_dut.tweet(CheerLightColours.GREEN)
        assert alt_dut.last_tweet_text.startswith(f'test tweet green with random value '
                                                  f'{alt_dut.last_random_value:d}')





