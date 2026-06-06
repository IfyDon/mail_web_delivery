"""Custom template filters for the marketing site."""
from django import template

register = template.Library()


@register.filter(name='split')
def split(value, delimiter=','):
    """Split a string by *delimiter* and return a list.

    Usage: {{ "a,b,c"|split:"," }}  →  ['a', 'b', 'c']
    """
    return str(value).split(delimiter)
