from django.utils import translation

def activate_user_language(request):
    if request.user.is_authenticated:
        try:
            language = request.user.userpreference.language
            translation.activate(language)
            request.LANGUAGE_CODE = language
        except:
            pass

    return {}