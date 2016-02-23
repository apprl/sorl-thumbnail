from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponsePermanentRedirect, Http404
from django.core.urlresolvers import reverse, resolve

from apparelrow.profile.forms import ProfileImageForm, ProfileAboutForm

def avatar_change(view_func):
    """
    Handle profile image/about form.
    Must be decorated after @get_current_user
    """
    def _decorator(request, profile, *args, **kwargs):
        if request.method == 'POST':
            if profile != request.user:
                return HttpResponseForbidden()

            if request.POST.get('change_image_form'):
                image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
                if image_form.is_valid():
                    image_form.save()

                    return HttpResponseRedirect(request.get_full_path())
            else:
                image_form = ProfileImageForm(instance=profile)

        else:
            image_form = ProfileImageForm(instance=profile)

        forms = [('change_image_form', image_form)]

        return view_func(request, profile, forms, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator


def get_current_user(view_func):
    """
    """
    def _decorator(request, slug=None, *args, **kwargs):
        if not slug:
            if not request.user.is_authenticated():
                return HttpResponseRedirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

            user = request.user
        else:
            try:
                user = get_user_model().objects.get(slug=slug)
            except get_user_model().DoesNotExist:
                try:
                    user = get_user_model().objects.get(username=slug)
                    if user.slug:
                        url_result = resolve(request.path)

                        return HttpResponsePermanentRedirect(reverse(url_result.url_name, args=[user.slug]))
                except get_user_model().DoesNotExist:
                    raise Http404()

        return view_func(request, user, *args, **kwargs)

    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__

    return _decorator
