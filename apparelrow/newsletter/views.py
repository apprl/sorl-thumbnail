from django import forms
from django.http import HttpResponse

from newsletter.models import Newsletter

#
# Add to newsletter
#

class NewsletterForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = Newsletter
        exclude = ('created',)

def newsletter_add(request):
    """
    Add email to newsletter list.
    """
    form = NewsletterForm(request.POST)
    response = HttpResponse()
    if form.is_valid():
        form.save()
        response.status_code = 202
    else:
        response.status_code = 400

    return response
