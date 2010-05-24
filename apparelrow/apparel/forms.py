from django.forms import ModelForm, CharField, Textarea
from apparel.models import *

class LookForm(ModelForm):
    tags = CharField(widget=Textarea)
    class Meta:
        model = Look
        exclude = ('products','user')

class LookComponentForm(ModelForm):
    class Meta:
        model = LookComponent
