from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse

from apparelrow.profile.forms import ProfileImageForm, ProfileAboutForm


def login_flow(view_func):
    """
    Login flow decorator. If login flow already is complete, redirect to user
    activity feed.
    """
    def _decorator(request, profile, *args, **kwargs):
        if profile.login_flow == 'complete':
            return HttpResponseRedirect(reverse('user_feed'))

        return view_func(request, profile, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator

def avatar_change(view_func):
    """
    Handle profile image/about form.

    Must be decorated after @get_current_user
    """
    def _decorator(request, profile, *args, **kwargs):
        if request.method == 'POST':
            if profile != request.user:
                return HttpResponseForbidden()

            if request.POST.get('change_image_form') or request.POST.get('change_about_form'):
                success = False

                image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
                if image_form.is_valid():
                    image_form.save()
                    success = True

                about_form = ProfileAboutForm(request.POST, request.FILES, instance=profile)
                if about_form.is_valid():
                    about_form.save()
                    success = True

                if success:
                    return HttpResponseRedirect(request.get_full_path())
            else:
                image_form = ProfileImageForm(instance=profile)
                about_form = ProfileAboutForm(instance=profile)

        else:
            image_form = ProfileImageForm(instance=profile)
            about_form = ProfileAboutForm(instance=profile)

        forms = [('change_image_form', image_form),
                 ('change_about_form', about_form)]

        return view_func(request, profile, forms, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator
