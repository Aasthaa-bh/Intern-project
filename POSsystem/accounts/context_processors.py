from .models import UserPreference

def user_preferences(request):
    if request.user.is_authenticated:
        preferences, created = UserPreference.objects.get_or_create(user=request.user)
        return {"preferences": preferences}

    return {}