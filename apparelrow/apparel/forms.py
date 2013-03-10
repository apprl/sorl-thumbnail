from django.forms import ModelForm, CharField, Textarea
from django.utils.translation import ugettext_lazy as _

from apparelrow.apparel.models import Look, LookComponent

class LookForm(ModelForm):
    title = CharField(error_messages={'required': _('You have to name your look before your create it.')})
    class Meta:
        model = Look
        exclude = ('tags', 'products', 'user', 'gender', 'popularity', 'width', 'height')

class LookComponentForm(ModelForm):
    class Meta:
        model = LookComponent
