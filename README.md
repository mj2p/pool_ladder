# Pool Ladder
### A simple Django app to track matches in a pool [ladder tournament](https://en.wikipedia.org/wiki/Ladder_tournament)

[![CircleCI](https://circleci.com/gh/mj2p/pool_ladder/tree/master.svg?style=svg)](https://circleci.com/gh/mj2p/pool_ladder/tree/master)  

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/mj2p/pool_ladder/tree/master)  
(post deployment, remember to run `python manage.py createsuperuser` in the Heroku shell)

## Description
Players can challenge opponents up to 2 places above them to a match.  
The winning player moves up, the loser moves down.  
If a match isn't played in time, the challenger automatically wins.  
If a player is "balled" (loses with all their balls still on the table) they move to the bottom of the ladder.

## Features
* User registration with email confirmation.
* Email notification of challenges.
* Slack notification of challenges and match results.
* Configurable match time out.
* Seasons - An admin can start a new season to shuffle the ladder.
* Players that have been challenged can extend the match time out.
* If a player has been challenged twice in a row, they can decline the next challenge.
* Runs on Heroku
* Progamatically fetch match data from the <url>/match-data/<season_id or '0' for all > endpoint (use shared secret as declared in variables below)

## Installation
#### Basic App
The pool ladder application is a Django app that utilises Channels for async operations.  
Channels will require an instance of [Redis](https://redis.io/) to be available.  
The app uses the Amazon S3 option from [django-storages](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html) to store static files so a set of AWS keys will need to be generated with appropriate iAM permissions (full S3 access works well).  
If you want to use email notifications, the key pair should have SES permissions too.  
  
Other than that, a standard Django deployment of Nginx > Gunicorn > Django will work.  
[This](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04) could help for background reading.  
  
  In short:
```bash
git clone https://github.com/mj2p/pool_ladder
cd pool_ladder
python3 -m venv ve
. ve/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///db.sqlite3
runserver 0.0.0.0:8000
```

As seen in the commands above, the main configuration is from environment variables. 
There is a portion of code in settings.py that loads variables from a json file called `.env` in the project root
This file should contain the following keys:

`DATABASE_URL`: Database URL in format expected by [dj-database-url](https://github.com/jacobian/dj-database-url#url-schema)    
`REDIS_URL`: The URL where Redis can be reached (usually `redis://localhost:6379`)  
`LADDER_NAME`: The name of your Pool Ladder. This is displayed on the site header.  
`SECRET_KEY`: The Django secret key used for secure signing. Keep this secret.  
`DEBUG`: Set this to `true` to enable debugging. Ensure this is `false` in production.   
`AWS_ACCESS_KEY_ID`: Key ID for AWS identity with S3/SES access.  
`AWS_SECRET_ACCESS_KEY`: Secret Key for AWS identity with S3/SES access.  
`AWS_STORAGE_BUCKET_NAME`: S3 Bucket name to use for static files storage.  
`FROM_EMAIL`: (optional) Email address that site mail comes from. leave blank to disable email.  
`SLACK_WEBHOOK_URL`: (optional) Slack [Webhook](https://api.slack.com/incoming-webhooks) for notifying a slack channel.  
`DATA_SECRET_TOKEN`: (optional) Secret to use for getting match data programatically. A header should be passed with a request like this `'HTTP-AUTH-TOKEN': 'pool-token {}'.format(secret_token)'`






 
