from django.forms import ModelForm
from beta.models import *

class InviteRequestForm(ModelForm):
    class Meta:
        model = InviteRequest
