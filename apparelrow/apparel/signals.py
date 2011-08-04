import django.dispatch

like = django.dispatch.Signal(providing_args=['instance', 'request'])
unlike = django.dispatch.Signal(providing_args=['instance', 'request'])
