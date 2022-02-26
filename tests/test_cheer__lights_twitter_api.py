import os

from random import randint
import sys
import time

import pytest

from cheer_lights_twitter_api import CheerLightTwitterAPI
from cheer_lights_twitter_api import CheerLightColours
from cheer_lights_twitter_api.tweepy_wrapper import TweepyWrapper
from cheer_lights_twitter_api import TwitterAPIVersion


@pytest.mark.parametrize("twitter_api_version", TwitterAPIVersion)
def test_tweet_unit_test(twitter_api_version, mocked_tweepy):
    """
    test that the tweets are made using a mock tweepy
    """
    class V1TweetReturn:
        def __init__(self):
            self.id = 1

    dut = CheerLightTwitterAPI(key_path='..', twitter_api_version=twitter_api_version)  # the path should never get used
    dut.connect()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    mocked_tweepy['tweepy_api_patch'].return_value.update_status.return_value = V1TweetReturn()
    tweet_id = dut.colour_template_tweet('blue')
    if twitter_api_version is TwitterAPIVersion.V1:
        mocked_tweepy['tweepy_client_patch'].return_value.create_tweet.assert_not_called()
        mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_called_once_with('@cheerlights blue')
        assert tweet_id == 1
        mocked_tweepy['tweepy_api_patch'].return_value.update_status.reset_mock()
    elif twitter_api_version is TwitterAPIVersion.V2:
        mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_not_called()
        mocked_tweepy['tweepy_client_patch'].return_value.create_tweet.assert_called_once_with(text='@cheerlights blue')
        assert tweet_id == 1
        mocked_tweepy['tweepy_api_patch'].return_value.update_status.reset_mock()
    dut.disconnect()


@pytest.mark.parametrize("twitter_api_version", TwitterAPIVersion)
def test_supressed_tweet_unit_test(twitter_api_version, mocked_tweepy):
    """
    test that the tweets are not made id the suppress_tweeting option is selected
    """
    dut = CheerLightTwitterAPI(key_path='..', suppress_tweeting=True, twitter_api_version=twitter_api_version)
    dut.connect()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.colour_template_tweet('blue')
    mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_not_called()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.disconnect()


@pytest.mark.parametrize("twitter_api_version", TwitterAPIVersion)
def test_supressed_connection_unit_test(twitter_api_version, mocked_tweepy):
    """
    test that the tweets are not made id the suppress_tweeting option is selected
    """
    dut = CheerLightTwitterAPI(key_path='..', suppress_tweeting=True, suppress_connection=True,
                               twitter_api_version=twitter_api_version)
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.connect()
    mocked_tweepy['tweepy_api_patch'].assert_not_called()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.colour_template_tweet('blue')
    mocked_tweepy['tweepy_api_patch'].return_value.update_status.assert_not_called()
    mocked_tweepy['tweepy_api_patch'].reset_mock()
    dut.disconnect()


def test_tweet_payload():
    """
    test that the tweets are correctly formed with the base template
    """
    dut = CheerLightTwitterAPI(key_path='illegal_path')  # the path should never get used
    # no need to connect to just test the payload generation

    # check a few manually
    payload = dut.colour_template_payload(colour=CheerLightColours.RED)
    assert payload == '@cheerlights red'

    payload = dut.colour_template_payload(colour=CheerLightColours.BLUE)
    assert payload == '@cheerlights blue'

    payload = dut.colour_template_payload(colour=CheerLightColours.RED)
    assert payload == '@cheerlights red'

    payload = dut.colour_template_payload(colour='magenta')
    assert payload == '@cheerlights magenta'

    payload = dut.colour_template_payload(colour='orange')
    assert payload == '@cheerlights orange'

    # check some bad inputs
    with pytest.raises(TypeError):
        payload = dut.colour_template_payload(colour=0xFFFFFF)

    with pytest.raises(ValueError):
        payload = dut.colour_template_payload(colour='darkblue')

    # loop through all the colours
    for colour in CheerLightColours:
        payload = dut.colour_template_payload(colour=colour)
        assert payload == f'@cheerlights {colour.name.lower()}'


def test_custom_template_with_static_context():
    """
    test overloading the jinja template with a custom template
    """

    file_path = os.path.dirname(__file__)
    custom_templates = os.path.join(file_path, 'custom_template_static_context')

    custom_context = {
        'user': 'Bob'
    }

    dut = CheerLightTwitterAPI(key_path='illegal_path',  # the path should never get used
                               user_template_dir=custom_templates,
                               user_template_context=custom_context)
    # no need to connect to just test the payload generation
    payload = dut.colour_template_payload(colour='orange')
    assert payload == '@cheerlights orange from Bob'


def test_custom_template_with_dynamic_context():
    """
    test overloading the jinja template with a custom template
    """

    file_path = os.path.dirname(__file__)
    custom_templates = os.path.join(file_path, 'custom_template_dynamic_context')

    dut = CheerLightTwitterAPI(key_path='illegal_path',  # the path should never get used
                               user_template_dir=custom_templates)
    # no need to connect to just test the payload generation
    payload = dut.colour_template_payload(colour='orange', jinja_context={'other_user':'Alice'})
    assert payload == '@cheerlights orange to Alice'
    payload = dut.colour_template_payload(colour='orange', jinja_context={'other_user': 'Jennie'})
    assert payload == '@cheerlights orange to Jennie'


def test_custom_template_with_static_and_dynamic_context():
    """
    test overloading the jinja template with a custom template
    """

    file_path = os.path.dirname(__file__)
    custom_templates = os.path.join(file_path, 'custom_template_dynamic_and_static_context')

    custom_context = {
        'user': 'Bob'
    }

    dut = CheerLightTwitterAPI(key_path='illegal_path',  # the path should never get used
                               user_template_dir=custom_templates,
                               user_template_context=custom_context)
    # no need to connect to just test the payload generation
    payload = dut.colour_template_payload(colour='orange', jinja_context={'other_user': 'Alice'})
    assert payload == '@cheerlights orange from Bob to Alice'
    payload = dut.colour_template_payload(colour='orange', jinja_context={'other_user': 'Jennie'})
    assert payload == '@cheerlights orange from Bob to Jennie'
    payload = dut.colour_template_payload(colour='orange', jinja_context={'other_user': 99})
    assert payload == '@cheerlights orange from Bob to 99'


@pytest.mark.integration_test
@pytest.mark.parametrize("twitter_api_version", TwitterAPIVersion)
def test_tweet(twitter_api_version):
    """
    test sending a tweet
    """

    class TestTwitterAPI(TweepyWrapper):
        """
        local class with overloaded method
        """

        def __init__(self, twitter_api_version):

            super().__init__(key_path='..', twitter_api_version=twitter_api_version)

            self.last_random_value = 0

        def test_tweet(self) -> int:

            self.last_random_value = randint(0, 2**32)

            payload = f'test tweet with random value {self.last_random_value:d} on ' \
                      f'Python {sys.version_info.major}.{sys.version_info.minor}'

            return super().tweet(payload=payload)

    # test with manual connect disconnect
    dut = TestTwitterAPI(twitter_api_version)

    # sending a tweet without connection should create an error
    with pytest.raises(RuntimeError):
        dut.test_tweet()

    dut.connect()

    tweet_sent_id = dut.test_tweet()
    time.sleep(10)
    tweets = dut.user_tweets(count=10)
    for tweet in tweets:
        if tweet.tweet_id == tweet_sent_id:
            dut.destroy_tweet(tweet_id=tweet.tweet_id)
            break
    else:
        assert False
    dut.disconnect()

    # test in a context manager
    with TestTwitterAPI(twitter_api_version) as alt_dut:
        tweet_sent_id = alt_dut.test_tweet()
        time.sleep(10)
        tweets = alt_dut.user_tweets(count=10)
        for tweet in tweets:
            if tweet.tweet_id == tweet_sent_id:
                alt_dut.destroy_tweet(tweet_id=tweet.tweet_id)
                break
        else:
            assert False
