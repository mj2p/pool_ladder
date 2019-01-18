from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PoolLadderConfig(AppConfig):
    name = 'pool_ladder'
    verbose_name = _('pool_ladder')

    def ready(self):
        import pool_ladder.signals  # noqa
