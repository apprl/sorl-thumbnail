from django.forms import ModelForm
from apparel.models import *

class LookForm(ModelForm):
    class Meta:
        model = Look
        exclude = ('products',)

class LookProductForm(ModelForm):
    class Meta:
        model = LookProduct
