import json

import requests
from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils.timezone import now

from pool_ladder.models import UserProfile, Match


class MainConsumer(JsonWebsocketConsumer):
    def connect(self):
        """
        Add channel to the necessary groups. Initiate data scan
        """
        # accept the websocket connection
        self.accept()

        # add the channel to the necessary groups
        async_to_sync(self.channel_layer.group_add)('pool_ladder', self.channel_name)

        print('Connected {} to pool_ladder group'.format(self.channel_name))

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    def disconnect(self, close_code):
        """
        disconnect from the websocket so remove from groups
        """
        async_to_sync(self.channel_layer.group_discard)('pool_ladder', self.channel_name)
        self.close()

    def send_users(self, event):
        """
        update the user ladder
        """
        # clear the table
        self.send(json.dumps({'message_type': 'users'}))

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    def send_challenges(self, event):
        """
        update the matches to be played
        """
        # clear the table
        self.send(json.dumps({'message_type': 'challenges'}))

        if not event.get('ignore_users'):
            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'send.users'
                }
            )

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    def send_matches(self, event):
        """
        update the played matches
        """
        # clear the table
        self.send(json.dumps({'message_type': 'matches'}))

        if not event.get('ignore_users'):
            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'send.users'
                }
            )

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    def receive(self, text_data):
        try:
            json_data = json.loads(text_data)
        except ValueError:
            return

        message_type = json_data.get('message_type')

        if message_type is None:
            return

        if message_type == 'challenge':
            challenger = self.scope['user']

            try:
                opponent = User.objects.get(pk=json_data.get('opponent'))
            except User.DoesNotExist:
                return

            if not challenger.userprofile.is_available:
                return

            if not opponent.userprofile.is_available:
                return

            Match.objects.create(
                challenger=challenger,
                opponent=opponent,
                challenger_rank=challenger.userprofile.rank,
                opponent_rank=opponent.userprofile.rank
            )

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    @staticmethod
    def check_challenges(event):
        """
        Ensure that no challenge has expired
        """
        for challenge in Match.objects.filter(played__isnull=True):
            if challenge.time_until < now():
                # challenge has timed out so the challenger automatically wins
                challenge.start_match()

                game_0 = challenge.game_set.get(index=0)
                game_0.winner = challenge.challenger
                game_0.save()

                game_1 = challenge.game_set.get(index=0)
                game_1.winner = challenge.challenger
                game_1.save()

                challenge.set_winner_and_loser()
                challenge.save()


class NotificationConsumer(SyncConsumer):
    @staticmethod
    def email(event):
        """
        send a challenge by email
        """
        if settings.FROM_EMAIL:
            send_mail(
                'Pool Ladder Challenge',
                '{} has challenged you to a {} match.\n'
                'It needs to be played by {} or you will forfeit'.format(
                    event.get('challenger'),
                    settings.LADDER_NAME,
                    event.get('time_until')
                ),
                '<{}>{}'.format(settings.FROM_EMAIL, settings.LADDER_NAME),
                [
                    event.get('email')
                ]
            )
            print('notified {} by email'.format(event.get('email')))

    @staticmethod
    def slack(event):
        """
        Send challenge notification by slack
        """
        if settings.SLACK_WEBHOOK_URL:
            requests.post(
                url=settings.SLACK_WEBHOOK_URL,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(
                    {
                        'text': event.get('message')
                    }
                )
            )
            print('notified by slack')
