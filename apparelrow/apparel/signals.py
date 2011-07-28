import django.dispatch

like = django.dispatch.Signal(providing_args=['instance'])
unlike = django.dispatch.Signal(providing_args=['instance'])
