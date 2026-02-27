from django.shortcuts import redirect

def owner_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.role != "OWNER":
            return redirect("login")

        return view_func(request, *args, **kwargs)
    return wrapper