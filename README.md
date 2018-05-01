# slackers
A collection of Slack bots.

## Getting started
1. Create a virtual environment based on python3.
2. Get the python requirements: `pip install -r requirements.txt`
3. Create a slackers.cfg (see: slackers.cfg.example)

## ec2bot
1. Create an SQS queue (called `awsmonitor` for this example)
2. Create a new CloudWatch Rule with a source of `aws.ec2` and a target of `awsmonitor`
3. Create a Slack Bot (Workspace -> Manage Apps -> Custom Integrations -> Bots -> Add Configuration)
4. Edit slackers.cfg with your slack token, SQS queue name, and channel name.
5. Start up the bot! `python ec2bot.py slackers.cfg`

### Required tags
Nag the slack channel when instances start up that are missing this list of tags. REQUIRED_TAGS should be a comma separated list of tags that should be present on every instance.
