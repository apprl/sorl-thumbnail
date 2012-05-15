import django.dispatch

user_created_with_email = django.dispatch.Signal(providing_args=['user'])
