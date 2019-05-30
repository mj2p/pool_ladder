from django.core.management import BaseCommand

from pool_ladder.models import Season, Match


class Command(BaseCommand):
    def handle(self, *args, **options):
        # create season 1
        earliest_match = Match.objects.all().order_by('challenge_time').first()
        season_1 = Season.objects.create(date_started=earliest_match.challenge_time, number=1)

        for match in Match.objects.all():
            match.season = season_1
            match.save()
