from django.core.urlresolvers import reverse
from django.template import Library, Variable, TemplateSyntaxError, Node

from apparelrow.profile.models import Follow

register = Library()

@register.filter
def is_following_profile(profile, followee):
    """
    This filter returns True if profile is following followee.
    """
    return Follow.objects.filter(user=profile, user_follow=followee, active=True).exists()


class DisplayActivityFollowUrl(Node):
    def __init__(self, actor, follow):
        self.actor = Variable(actor)
        self.follow = follow

    def render(self, context):
        actor_instance = self.actor.resolve(context)
        try:
            if self.follow:
                return reverse('follow', kwargs={'profile_id': actor_instance.pk})

            return reverse('unfollow', kwargs={'profile_id': actor_instance.pk})
        except AttributeError, msg:
            # This inactivates the Follow button due the user does not exist
            pass

@register.tag
def unfollow_tag(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError, "Accepted format {% unfollow_tag [instance] %}"
    else:
        return DisplayActivityFollowUrl(bits[1], False)

@register.tag
def follow_tag(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError, "Accepted format {% follow_tag [instance] %}"
    else:
        return DisplayActivityFollowUrl(bits[1], True)
