from django.dispatch import receiver
from django_registration.signals import user_registered

from pool_ladder.models import UserProfile


@receiver(user_registered)
def create_user_profile(sender, **kwargs):
    user = kwargs.get('user')

    profile = UserProfile.objects.create(
        user=user,
        rank=(UserProfile.objects.all().count() + 1)
    )

    print('created profile {} for {}'.format(profile, user))
