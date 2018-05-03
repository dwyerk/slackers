import markovify
import json
import time
from slackclient import SlackClient
import random
import configparser

CONFIGS = configparser.ConfigParser()
CONFIGS.read('slackers.cfg')
CONFIG = CONFIGS['wybott']

def get_model(model_path):
    with open(model_path) as f:
        model_json = f.read()
        model = markovify.Text.from_json(model_json)
        return model

def parse_slack_output(slack_output, my_id):
    mentioned = False
    mentioned_channel = None
    if slack_output:
        for output in slack_output:
            print("got: ", output)
            if 'type' in output and output['type'] != 'message':
                continue
            if 'subtype' in output and output['subtype'] == 'message_changed':
                continue
            #if 'text' in output: print(output['text'])

            if 'user' in output:
                print("my id", my_id, output['user'])
            if ('user' in output and output['user'] == my_id):
                # this is me, ignore
                continue

            # someone is mentioning me:
            if (('text' in output and '<@' + my_id + '>' in output['text']) or
                # someone is DMing me:
                ('channel' in output and output['channel'].startswith('D'))):
                mentioned = True
                mentioned_channel = output['channel']
    return mentioned, mentioned_channel

def been_a_while(last_time):
    diff = time.time() - last_time
    #print("diff:", diff)
    if diff > CONFIG.getfloat('AWHILE'):
        #print("diff:", diff)
        return random.random() * diff > CONFIG.getfloat('AWHILE')
    return False

def normal_work_day():
    now = time.localtime()
    if (now.tm_hour >= 9 and now.tm_hour < 16
        and now.tm_wday < 5):
        print("normal_work_day!")
        return True
    return False

def sentence_length():
    return max(min(int(random.lognormvariate(0, 1) * 140), 500), 60)

def main():
    LOOP_TIMEOUT=.5
    last_time = 0
    # To make it not say anything on startup:
    last_time = time.time()
    my_channels = []
    model = get_model(CONFIG['MODEL_PATH'])
    print(model.make_short_sentence(sentence_length(), tries=1000))
    slack_client = SlackClient(CONFIG['SLACK_TOKEN'])
    if slack_client.rtm_connect():
        print("Connected to Slack")
        my_id = slack_client.server.login_data['self']['id']

        while True:
            mentioned, mentioned_channel = parse_slack_output(slack_client.rtm_read(), my_id)
            if CONFIG.getboolean('TEST_MODE'):
                my_channels = [{'id': CONFIG['TEST_CHANNEL_ID']}]
            else:
                try:
                    my_channels = [x for x in slack_client.api_call("channels.list")['channels'] if x['is_member'] and not x['name'] == CONFIG['TEST_CHANNEL']]
                except (KeyError, json.decoder.JSONDecodeError):
                    # sometimes channels isn't there?
                    pass

            # Under some criteria, write a message
            if mentioned or (been_a_while(last_time) and normal_work_day()):
                wisdom = model.make_short_sentence(sentence_length(), tries=1000)
                print('wisdom', wisdom)
                if wisdom:
                    if mentioned:
                        channel = {'id': mentioned_channel}
                    else:
                        channel = random.choice(my_channels)
                    slack_client.server.send_to_websocket({'id':1, 'type': 'typing', 'channel': channel['id']})
                    time.sleep(2)
                    slack_client.api_call("chat.postMessage", channel=channel['id'], text=wisdom, as_user=True)
                    last_time = time.time()

            time.sleep(LOOP_TIMEOUT)


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            print("well, this is embarassing")
            print(e)
            time.sleep(5000)

