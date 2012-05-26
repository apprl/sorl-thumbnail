from django.forms import ModelForm, CharField, Textarea
from django.utils.translation import ugettext_lazy as _

from apparel.models import Look, LookComponent

class LookForm(ModelForm):
    tags = CharField(widget=Textarea, required=False)
    title = CharField(error_messages={'required': _('You have to name your look before your create it.')})
    class Meta:
        model = Look
        exclude = ('products', 'user', 'gender', 'popularity')

class LookComponentForm(ModelForm):
    class Meta:
        model = LookComponent
