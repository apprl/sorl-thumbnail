from django.forms import ModelForm

from apparelrow.profile.models import ApparelProfile

class ProfileImageForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('image',)
