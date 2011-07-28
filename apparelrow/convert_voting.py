import os
import optparse

from django.core.management import setup_environ

usage = "usage: %prog -s SETTINGS | --settings=SETTINGS"
parser = optparse.OptionParser(usage)
parser.add_option('-s', '--settings', dest='settings', metavar='SETTINGS',
                  help="The Django settings module to use")
parser.add_option('-d', '--dry', action='store_true', dest='dry', default=False)
(options, args) = parser.parse_args()
if not options.settings:
    parser.error("You must specify a settings module")


settings = __import__('%s' % (options.settings,), fromlist=['apparelrow'])
setup_environ(settings)

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from apparelrow.apparel.models import Look, Product, LookLike, ProductLike
from voting.models import Vote
from actstream.models import Action

if options.dry:
    print 'Running in dry and verbose mode'

# Product
for vote in Vote.objects.filter(content_type=ContentType.objects.get_for_model(Product)):
    try:
        product = Product.objects.get(pk=vote.object_id)
    except ObjectDoesNotExist, MultipleObjectsReturned:
        if options.dry:
            print 'Would delete vote because we did not found product or we found more then one product with id %s' % (vote.object_id,)
        else:
            vote.delete()
        continue

    if options.dry:
        print 'Would create new product_like for %s %s' % (vote.user, product)
    else:
        ProductLike.objects.create(user=vote.user, product=product)

    if not options.dry:
        action_objects = Action.objects.filter(actor_object_id=vote.user.pk,
                                       verb='liked',
                                       action_object_content_type=ContentType.objects.get_for_model(vote),
                                       action_object_object_id=vote.pk)
        for action_object in action_objects:
            action_object.action_object_content_type = ContentType.objects.get_for_model(Product)
            action_object.action_object_object_id = product.pk
            action_object.verb = 'liked_product'
            action_object.save()

        vote.delete()

# Look
for vote in Vote.objects.filter(content_type=ContentType.objects.get_for_model(Look)):
    try:
        look = Look.objects.get(pk=vote.object_id)
    except ObjectDoesNotExist, MultipleObjectsReturned:
        if options.dry:
            print 'Would delete vote because we did not found look or we found more then one look with id %s' % (vote.object_id,)
        else:
            vote.delete()
        vote.delete()
        continue

    if options.dry:
        print 'Would create new look_like for %s %s' % (vote.user, look)
    else:
        LookLike.objects.create(user=vote.user, look=look)

    if not options.dry:
        action_objects = Action.objects.filter(actor_object_id=vote.user.pk,
                                       verb='liked',
                                       action_object_content_type=ContentType.objects.get_for_model(vote),
                                       action_object_object_id=vote.pk)
        for action_object in action_objects:
            action_object.action_object_content_type = ContentType.objects.get_for_model(Look)
            action_object.action_object_object_id = look.pk
            action_object.verb = 'liked_look'
            action_object.save()

        vote.delete()
