import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
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

        self.send_users({})
        self.send_challenges({})
        self.send_matches({})

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
        send the user ladder
        """
        # clear the table
        self.send(json.dumps({'message_type': 'clear_users'}))

        max = UserProfile.objects.all().count()

        for profile in UserProfile.objects.all():
            self.send_json(
                {
                    'message_type': 'user_ladder',
                    'user': render_to_string(
                        'pool_ladder/fragments/user.html',
                        {
                            'profile': profile,
                            'can_challenge': profile.can_challenge(self.scope["user"]),
                            'swag': '1f478' if profile.rank == 1 else '1F4A9;' if profile.rank == max else ''
                        }
                    )
                }
            )

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'check.challenges'
            }
        )

    def send_challenges(self, event):
        """
        send the matches to be played
        """
        # clear the table
        self.send(json.dumps({'message_type': 'clear_challenges'}))

        for challenge in Match.objects.filter(played__isnull=True):
            self.send_json(
                {
                    'message_type': 'challenge',
                    'challenge': render_to_string(
                        'pool_ladder/fragments/challenge.html',
                        {'challenge': challenge}
                    )
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
        send the matches to be played
        """
        # clear the table
        self.send(json.dumps({'message_type': 'clear_matches'}))

        for match in Match.objects.exclude(played__isnull=True):
            self.send_json(
                {
                    'message_type': 'match',
                    'match': render_to_string(
                        'pool_ladder/fragments/match.html',
                        {'match': match}
                    )
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
                # challenge has times out so the challenger automatically wins
                challenge.start_match()

                game_0 = challenge.game_set.get(index=0)
                game_0.winner = challenge.challenger
                game_0.save()

                game_1 = challenge.game_set.get(index=0)
                game_1.winner = challenge.challenger
                game_1.save()

                challenge.set_winner_and_loser()
                challenge.save()
