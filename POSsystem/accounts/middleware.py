# accounts/middleware.py

from django.utils import translation


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, "preferences"):
            language = request.user.preferences.language or "en"

            if language not in ["en", "ne"]:
                language = "en"

            translation.activate(language)
            request.LANGUAGE_CODE = language
            request.session["django_language"] = language

        response = self.get_response(request)
        return response