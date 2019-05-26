from django import template
from django.conf import settings

register = template.Library()


@register.filter
def ladder_name(value):
    """
    Return ladder name from settings
    """
    set_name = settings.LADDER_NAME
    return set_name or 'Ripjar Pool Ladder'
