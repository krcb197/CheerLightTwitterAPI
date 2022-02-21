"""
Common fixtures for the tests
"""

import pytest

def pytest_addoption(parser):
    parser.addoption("--integration_test", action="store_true",
                     default=False, help="runs the integration test - these will send live tweets")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration_test"):
        no_integration_test = pytest.mark.skip(reason="need --integration_test option to run")
        for item in items:
            if "integration_test" in item.keywords:
                item.add_marker(no_integration_test)

@pytest.fixture()
def mocked_tweepy(mocker):

    tweepy_api_patch = mocker.patch('cheer_lights_twitter_api.tweepy_wrapper.tweepy.API')
    tweepy_auth_handler_patch = mocker.patch('cheer_lights_twitter_api.tweepy_wrapper.tweepy.OAuth1UserHandler')

    yield {'tweepy_api_patch':tweepy_api_patch,
           'tweepy_auth_handler_patch' : tweepy_auth_handler_patch}