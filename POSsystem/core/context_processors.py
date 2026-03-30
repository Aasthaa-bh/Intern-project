from core.utils import get_business_type_code

def business_context(request):
    business = getattr(request.user, "business", None) if request.user.is_authenticated else None
    return {
        "current_business": business,
        "current_business_type": get_business_type_code(request.user) if request.user.is_authenticated else None,
    }