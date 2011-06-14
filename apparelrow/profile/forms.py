from django.forms import ModelForm
from profile.models import *

class ProfileForm(ModelForm):
    class Meta:
        model = ApparelProfile
        exclude = ('user', 'name')
