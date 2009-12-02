import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext, ugettext_lazy as _


class StoredQuery(models.Model):
    user     = models.ForeignKey(User, related_name='watches')
    name     = models.CharField(max_length=20)
    query    = models.CharField(max_length=255)

    def save(self, force_insert=False, force_update=False):
        if not self.name:
            self.name = u'%s %s' % (
                ugettext("Search"),
                StoredQuery.objects.filter(user=self.user).count() + 1
            )
        
        super(StoredQuery, self).save(force_insert=force_insert, force_update=force_update)
                
    class Meta:
        unique_together = (('user', 'name'),)
    
    def __unicode__(self):
        return u'%s' % self.name

class StoredQueryByEmail(models.Model):
    stored_query = models.OneToOneField(StoredQuery, related_name='by_email')
    checked      = models.DateTimeField(_('Time last checked'), null=True, blank=True)
    success      = models.NullBooleanField(_('E-mail successfully sent'), null=True)
    reason       = models.CharField(_('Why e-mail was not sent'), max_length=100, null=True, blank=True)

    def __unicode__(self):
        return u'%s (e-mail)' % self.watch.name

