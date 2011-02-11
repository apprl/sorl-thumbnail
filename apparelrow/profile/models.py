import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import get_language, ugettext_lazy as _
from django.db.models.signals import post_save
from django_facebook.models import FacebookProfile
import settings

from voting.models import Vote
from apparel.models import Look


import datetime, mptt

# FIXME: Move to Django settings directory
PROFILE_BASE      = 'static/profile'

class ApparelProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    name  = models.CharField(max_length=50, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to=PROFILE_BASE, help_text=_('User profile image'), blank=True, null=True) 
    about = models.TextField(_('About'), null=True, blank=True)

    @models.permalink
    def get_looks_url(self):
        return ('looks_by_user', [str(self.user.username)])

    # FIXME: Extract number of looks and and likes

    @property
    def looks(self):
        # Number of looks
        return Look.objects.filter(user=self.user).count()
    
    @property
    def likes(self):
        return Vote.objects.filter(user=self.user).count()

    @property
    def display_name(self):
        if self.name is not None:
            return self.name
        
        if self.user.first_name:
            return u'%s %s' % (self.user.first_name, self.user.last_name)
         
        return u'%s' % self.user

    @property
    def avatar(self):
        # FIXME: Scale to 30x30
        if self.image:
            return '/scale/52%s' % self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def avatar_large(self):
        if self.image:
            return self.image

        if self.facebook_profile:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_profile.uid

        return settings.APPAREL_DEFAULT_AVATAR

    @property
    def facebook_profile(self):
        try:
            return FacebookProfile.objects.get(user=self.user)
        except FacebookProfile.DoesNotExist:
            return None

    @models.permalink
    def get_absolute_url(self):
        return ('profile.views.profile', [str(self.user.username)])
    
    def __unicode__(self):
        return self.display_name

def create_profile(signal, instance, **kwargs):
    if kwargs['created']:
        p = ApparelProfile(user=instance)
        p.save()

def create_profile_from_facebook(signal, instance, **kwargs):
    if kwargs['created']:
        p = ApparelProfile(user=instance.user)
        p.name = instance.name
        p.about = instance.bio
        p.save()

post_save.connect(create_profile, sender=User)
post_save.connect(create_profile_from_facebook, sender=FacebookProfile)
