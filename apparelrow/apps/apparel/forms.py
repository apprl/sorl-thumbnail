from django.forms import ModelForm
from apparel.models import *

class LookProductForm(ModelForm):
    class Meta:
        model = LookProduct
