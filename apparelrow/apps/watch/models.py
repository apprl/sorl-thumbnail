import logging
from django.db import models
from django.contrib.auth.models import User


class Watch(models.Model):
    user     = models.ForeignKey(User, related_name='watches')
    name     = models.CharField(max_length=20)
    query    = models.CharField(max_length=255)

    class Meta:
        unique_together = (('user', 'name'),)
    
    __unicode__(self):
        return u'%s' % self.name

class WatchEmail(models.Model):
    watch    = models.OneToOneField(Watch, related_name='by_email')
    checked  = models.DateTimeField(_('Time last checked'), null=True, blank=True)
    success  = models.Booleanfield(_('E-mail successfully sent'), null=True)
    reason   = models.CharField(_('Why e-mail was not sent'), max_length=100, null=True, blank=True)

    __unicode__(self):
        return u'%s (e-mail)' % self.watch.name

