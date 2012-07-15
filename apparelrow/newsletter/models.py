from django.db import models

#
# Newsletter
#

class Newsletter(models.Model):
    email = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __unicode__(self):
        return '%s' % (self.email,)
