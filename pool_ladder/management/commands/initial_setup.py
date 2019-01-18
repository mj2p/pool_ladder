from django.core.management import BaseCommand


class Command(BaseCommand):
    names = ['Leigh', 'John', 'Chris', 'Ben', 'Jamie', 'Rich', 'Zak', 'Dave', 'Tom', 'Joe', 'Sam', 'Mark', 'Steve',
             'Drum', 'Mike']

    def handle(self, *args, **options):
        for name in self.names:
            pass
