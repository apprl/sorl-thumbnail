from django.forms import ModelForm
from apparel.models import *

class LookForm(ModelForm):
    class Meta:
        model = Look
        exclude = ('products','user')

class LookProductForm(ModelForm):
    class Meta:
        model = LookProduct
