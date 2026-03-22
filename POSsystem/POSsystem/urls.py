"""
URL configuration for POSsystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import set_language
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("kitchen/", RedirectView.as_view(pattern_name="restaurant_kitchen_dashboard", permanent=False)),
   path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path(
        "restaurant/", include("restaurant.urls"),
    ),
    path("pos/", include("pos.urls")),
    path("clothing/", include("clothing.urls")),
    path("", include("core.urls")),
    path("superadmin/", include("subscription.urls")),
    path("set-language/", set_language, name="set_language"),
    path("i18n/", include("django.conf.urls.i18n")),
]



from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
