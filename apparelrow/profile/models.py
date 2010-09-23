import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.db.models.signals import post_save
from socialregistration.models import FacebookProfile
import settings


import datetime, mptt

# FIXME: Move to Django settings directory
PROFILE_BASE      = 'static/profile'

# 
# FIXME: Let the facebook profile automatically update this object on authentication
# rather than constantly checking these properties
# 

class ApparelProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    name  = models.CharField(max_length=50, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to=PROFILE_BASE, help_text=_('User profile image'), blank=True, null=True) 

    @models.permalink
    def get_looks_url(self):
        return ('looks_by_user', [str(self.user.username)])

    @property
    def display_name(self):
        if self.name is not None:
            return self.name
            
        # FIXME Right now, we seem to only be able to get this in the view
        #if hasattr(self.user, 'facebook_profile'):
        #    return self.user.facebook_profile.first_name
        
        return u'%s' % self.user
    
    @property
    def avatar(self):
        if self.image:
            return self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def facebook_profile(self):
        try:
            return FacebookProfile.objects.get(user=self.user)
        except DoesNotExist:
            return None

    def __unicode__(self):
        return self.display_name

def create_profile(signal, instance, **kwargs):
    if kwargs['created']:
        p = ApparelProfile(user=instance)
        p.save()

post_save.connect(create_profile, sender=User)
