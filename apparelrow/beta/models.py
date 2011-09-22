from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _
from django.contrib.auth.models import User

from profile.models import ApparelProfile

class Invite(models.Model):
    code        = models.CharField(_('beta code'), max_length=10, blank=False)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.code, self.created)

class Invitee(models.Model):
    email       = models.EmailField(_('e-mail address'), blank=False)
    invite      = models.ForeignKey(Invite)
    created     = models.DateTimeField(_("Time created"), auto_now_add=True)
    seen        = models.DateTimeField(_("Time seen"), null=True, blank=True)
    used_count  = models.IntegerField(_('used count'), null=False, blank=False, default=0)

    def __unicode__(self):
        return u"%s (%s)" % (self.email, self.seen)

class InvitePerUser(models.Model):
    user = models.OneToOneField(ApparelProfile, related_name='beta')
    invites = models.IntegerField(_('invites'), null=False, blank=False, default=0)

    def __unicode__(self):
        return u'%s (%s invites)' % (self.user, self.invites)

class InviteRequest(models.Model):
    email = models.EmailField(_('E-mail address'))
    invitee = models.OneToOneField(Invitee, null=True)

    def __unicode__(self):
        return u"%s" % self.email
