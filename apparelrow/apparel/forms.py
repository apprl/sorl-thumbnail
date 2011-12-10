from django.forms import ModelForm, CharField, Textarea
from apparel.models import *

class LookForm(ModelForm):
    tags = CharField(widget=Textarea, required=False)
    class Meta:
        model = Look
        exclude = ('products', 'user', 'gender')

class LookComponentForm(ModelForm):
    class Meta:
        model = LookComponent
