from django import template
from django.utils import translation

register = template.Library()


@register.filter
def nepali_number(value):
    if translation.get_language() != "ne":
        return value

    eng = "0123456789"
    nep = "०१२३४५६७८९"

    value = str(value)
    for e, n in zip(eng, nep):
        value = value.replace(e, n)

    return value


@register.filter
def translate_category(value):
    if translation.get_language() != "ne":
        return value

    mapping = {
        "Cabin": "क्याबिन",
        "Indoor": "भित्र",
        "Outdoor": "बाहिर",
    }

    return mapping.get(str(value), value)


@register.filter
def translate_table_status(value):
    if translation.get_language() != "ne":
        return value

    mapping = {
        "AVAILABLE": "उपलब्ध",
        "OCCUPIED": "व्यस्त",
        "RESERVED": "आरक्षित",
        "CLEANING": "सफा हुँदै",
        "Available": "उपलब्ध",
        "Occupied": "व्यस्त",
        "Reserved": "आरक्षित",
        "Cleaning": "सफा हुँदै",
    }

    return mapping.get(str(value), value)

@register.filter
def translate_package_name(value):
    if translation.get_language() != "ne":
        return value

    mapping = {
        "Basic": "बेसिक",
        "Standard": "स्ट्यान्डर्ड",
        "Premium": "प्रिमियम",
    }

    return mapping.get(str(value), value)