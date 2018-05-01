import boto3
import botocore
from slackclient import SlackClient

from collections import namedtuple
import configparser
import json
import threading
import time
import queue
import sys

if len(sys.argv) < 2:
    print("ERROR: missing path to slackers.cfg")
    sys.exit(1)

CONFIGS = configparser.ConfigParser()
CONFIGS.read(sys.argv[1])
CONFIG = CONFIGS['ec2bot']
REQUIRED_TAGS = set(CONFIG['REQUIRED_TAGS'].split(','))

InstanceState = namedtuple(
    "InstanceState", ["instance_id", "state", "missing_tags", "found_tags"])

SHUTDOWN = False

def get_instance_state():
    ec2 = boto3.client('ec2')
    instances = ec2.describe_instances()

    missing = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            state = instance['State']['Name']
            tags = instance['Tags']

            tag_map = {}
            for tag in tags:
                tag_map[tag['Key']] = tag['Value']

            missing_tags = REQUIRED_TAGS - set(tag_map)

            missing.append(InstanceState(instance_id, state, missing_tags,
                                         tag_map))

    return missing

def parse_event(event):
    ec2 = boto3.client('ec2')
    instance_id = event['detail']['instance-id']
    try:
        desc = ec2.describe_instances(InstanceIds=[instance_id])
    except botocore.exceptions.ClientError:
        desc = {'Reservations': []}

    #print(desc)
    # Only non-terminated instances will have this
    if desc['Reservations']:
        instance = desc['Reservations'][0]['Instances'][0]
        tags = instance['Tags']

        tag_map = {}
        for tag in tags:
            tag_map[tag['Key']] = tag['Value']

        missing_tags = REQUIRED_TAGS - set(tag_map)

        msg = 'ec2 event: {}, id: {}, public_ip: {}, private_ip: {}, tags: {}' \
              .format(
                  event['detail']['state'],
                  instance_id,
                  instance.get('PublicIpAddress'),
                  instance.get('PrivateIpAddress'),
                  ', '.join(['{}={}'.format(k,v) for k,v in tag_map.items()]))

        if missing_tags:
            msg += '*missing tags: {}*'.format(', '.join(missing_tags))

        return msg

    return 'ec2 event: {}, id: {}'.format(
        event['detail']['state'],
        instance_id)

def get_ec2_events(msg_queue):
    sqs = boto3.resource('sqs')
    sqs_queue = sqs.get_queue_by_name(QueueName=CONFIG['EC2_EVENT_QUEUE_NAME'])

    while not SHUTDOWN:
        print("event loop iteration")
        processed_messages = []
        for i, message in enumerate(
                sqs_queue.receive_messages(WaitTimeSeconds=10)):
            processed_messages.append(
                {'Id': '{}'.format(i),
                 'ReceiptHandle': message.receipt_handle})

            body = json.loads(message.body)
            print("Incoming ec2 event: ", body)
            msg_queue.put(body)

        if processed_messages:
            sqs_queue.delete_messages(Entries=processed_messages)

def main(msg_queue, channel):
    LOOP_TIMEOUT=.5

    slack_client = SlackClient(CONFIG['SLACK_TOKEN'])
    if slack_client.rtm_connect():
        print("Connected to Slack")
        #my_id = slack_client.server.login_data['self']['id']
        # try:
        #     my_channels = [x for x in slack_client.api_call("channels.list")['channels'] if x['is_member']]
        # except (KeyError, json.decoder.JSONDecodeError):
        #     # sometimes channels isn't there?
        #     pass

        while not SHUTDOWN:
            try:
                event = msg_queue.get_nowait()
                print("New event:", event)
                parsed_event = parse_event(event)
                slack_client.api_call(
                    "chat.postMessage", channel=channel, text=parsed_event,
                    as_user=True)
            except queue.Empty:
                pass

            slack_msgs = slack_client.rtm_read()
            if slack_msgs:
                print(slack_msgs)
            time.sleep(LOOP_TIMEOUT)

if __name__ == '__main__':
    #instances = get_instance_state()

    # for missing in instances:
    #     print('{} instance {} missing tags: {} found: {}'.format(
    #         missing.state, missing.instance_id, ','.join(missing.missing_tags), missing.found_tags))

    while not SHUTDOWN:
        try:
            msg_bus = queue.Queue()
            eventsThread = threading.Thread(name="ec2events", target=get_ec2_events, args=[msg_bus])
            eventsThread.start()
            main(msg_bus, CONFIG['CHANNEL'])
            eventsThread.join()
        except KeyboardInterrupt as e:
            print("Shutting down")
            SHUTDOWN = True
        except Exception as e:
            print("well, this is embarassing")
            print(e)
            SHUTDOWN = True
            eventsThread.join()
            SHUTDOWN = False
            time.sleep(5000)

