from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def split(value, arg):
    """將字符串按指定分隔符分割"""
    if value is None:
        return ['']
    return value.split(arg)

@register.filter
def first(value):
    """獲取列表的第一個元素"""
    if not value:
        return ''
    return value[0] if value else ''
