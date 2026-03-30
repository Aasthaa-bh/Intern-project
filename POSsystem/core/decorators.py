from django.shortcuts import redirect
from functools import wraps

def owner_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.role != "OWNER":
            return redirect("login")

        return view_func(request, *args, **kwargs)
    return wrapper

def business_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        
        if not hasattr(request.user, 'business') or not request.user.business:
            return redirect("login")
        
        return view_func(request, *args, **kwargs)
    return wrapper