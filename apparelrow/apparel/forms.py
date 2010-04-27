from django.forms import ModelForm
from apparel.models import *

class LookForm(ModelForm):
    class Meta:
        model = Look
        exclude = ('products','user')

class LookComponentForm(ModelForm):
    class Meta:
        model = LookComponent
