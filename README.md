# CheerLightTwitterAPI
Generate tweets to for Cheerlights

# Installation

To install the required packages 

```bash
pip install -r requirements.txt
```

# Preparation

In order to use this library you will need twitter API keys, [How to get access to the Twitter API](https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api)

These are then accessed by the class in one of two ways (in this order of priority):

1. A file called ```twitter_credentials.json``` which is in the working directory (this is not 
   stored into GitHub), refer to ```example_twitter_credentials.json``` for the example format
2. Via the follow four environment variables, this is the recommended way to pass keys within a
   cloud enviroment e.g. GitHub:
      - ```TWITTER_API_KEY```
      - ```TWITTER_API_SECRET```
      - ```TWITTER_ACCESS_TOKEN```
      - ```TWITTER_ACCESS_SECRET```

# Usage

This can be used in one of two ways

## Command Application

The file can be called usin the command line:

For example to generate a tweet with the color red
```bash
python cheer_lights_twitter_api.py red
```
The command line help has the full list of colour and other options
```bash
python cheer_lights_twitter_api.py -h
```

## As a Python class

There are two ways to use the class:
- In a python context manager (the connection to the twitter is managed automagically)
- Where the connection is persistent (this would be the approach if the object is instantiated in
  another class )

### Context Manager Example
```python
# import the colour enum
from cheer_lights_twitter_api import CheerLightColours
# import the tweeting API class
from cheer_lights_twitter_api import CheerLightTwitterAPI

with CheerLightTwitterAPI() as cheer_lights:
    cheer_lights.tweet(CheerLightColours[CheerLightColours.RED])

```

### Manual Connect / Disconnect
```python
# import the colour enum
from cheer_lights_twitter_api import CheerLightColours
# import the tweeting API class
from cheer_lights_twitter_api import CheerLightTwitterAPI

cheer_lights = CheerLightTwitterAPI()
cheer_lights.connect()
# make a tweet with the colour red
cheer_lights.tweet(CheerLightColours[CheerLightColours.RED])
cheer_lights.disconnect()

```

# Advanced Usage

The payload of the tweet is constructed using [Jinja](https://jinja.palletsprojects.com/en/3.0.x/)
this is a templating language used in many web engines, it allows the payload of the tweet to
be changed without needing to edit the core code.

The payload can be edited by changing the the ```tweet.jinga``` file in the src.templates

However, if you want to change the template without changing the code from the repository you 
can do one of the following:

## Derived Class

Build a derived class from the ```CheerLightTwitterAPI``` and overload the ```tweet_payload```
method. At this poitn you are bypassing the all the jinja templates

```python
class MyCheerLightTwitterAPI(CheerLightTwitterAPI):

    def tweet_payload(self, colour: CheerLightColours) -> str:
        return f'My tweet {colour.name}'
```

## pass in a user Jinja template

When initialising the ```CheerLightTwitterAPI``` class pass in the string name for your own 
folder of templates and user context using for example:

put a file called ```tweet.jinja``` in a folder called ```custom_templates```. 

In this case we can extend the template with a new parameter: ```user```

```jinja
@cheerlights {{ colour }} from {{ user }}
```

In this case the ```CheerLightTwitterAPI``` is then created with a new context which extends
the jinja context with a new parameter called ```user```

```python
custom_context = {
        'user' : 'Bob'
    }

 dut = CheerLightTwitterAPI(user_template_dir='custom_templates',
                            user_template_context=custom_context)
 # no need to connect to just test the payload generation
 payload = dut.tweet(colour='orange')
```
This will create a tweet with the following payload: `@cheerlights orange from Bob`




