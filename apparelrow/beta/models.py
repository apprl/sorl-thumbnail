from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _

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

    def __unicode__(self):
        return u"%s (%s)" % (self.email, self.seen)
