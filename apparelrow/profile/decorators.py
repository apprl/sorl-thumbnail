from django.http import HttpResponseRedirect, HttpResponseForbidden

from profile.forms import ProfileImageForm

def avatar_change(view_func):
    """
    """
    def _decorator(request, profile, *args, **kwargs):
        if request.method == 'POST':
            if profile.user != request.user:
                return HttpResponseForbidden()

            form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(form.instance.get_absolute_url())
        else:
            form = ProfileImageForm(instance=profile)

        return view_func(request, profile, form, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator
