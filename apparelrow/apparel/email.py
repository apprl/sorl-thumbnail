# -*- coding: utf-8 -*-
import datetime
import csv
import StringIO

from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseNotFound
from django.db.models import Q, Count
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from actstream.models import Follow, Action
from sorl.thumbnail import get_thumbnail
from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException

from profile.models import ApparelProfile
from apparel.models import Product, Look

@login_required
def admin_user_list_csv(request):
    if not request.user.is_superuser:
        return HttpResponseNotFound()

    csv_string = StringIO.StringIO()

    writer = csv.writer(csv_string)
    for user in User.objects.exclude(Q(email__isnull=True) | Q(email__exact='')).exclude(Q(first_name__isnull=True) | Q(first_name__exact='')).exclude(Q(last_name__isnull=True) | Q(last_name__exact='')):
        writer.writerow([user.email.encode('utf-8'), user.first_name.encode('utf-8'), user.last_name.encode('utf-8')])

    response = HttpResponse(csv_string.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=apparelrow-users.csv'

    csv_string.close()

    return response

@login_required
def generate_weekly_mail(request):
    if not request.user.is_superuser:
        return HttpResponseNotFound()

    user_content_type = ContentType.objects.get_for_model(User)
    one_week_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)

    # Products
    product_names = []
    products = []
    base_products = list(Product.objects.filter(published=True, category__isnull=False, vendorproduct__isnull=False)
                                        .filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                        .order_by('-popularity')[:9])
    week_products = list(Product.objects.filter(published=True, category__isnull=False, vendorproduct__isnull=False)
                                        .filter(likes__active=True, likes__modified__gt=one_week_ago)
                                        .filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                        .annotate(num_likes=Count('likes')).order_by('-num_likes')[:9])

    used_products = []
    count_products = 0
    for product in week_products + base_products:
        if product.pk not in used_products:
            if product.manufacturer.name not in product_names:
                product_names.append(product.manufacturer.name)
            product_image = get_thumbnail(product.product_image, '176', crop='noop').url
            product_price = u'%.0f %s' % (product.default_vendor.price, product.default_vendor.currency)
            if product.default_vendor.discount_price:
                product_price = u'<span class="discount">%.0f %s</span> <span class="original">%.0f %s</span>' % (product.default_vendor.discount_price, product.default_vendor.currency, product.default_vendor.price, product.default_vendor.currency)

            products.append({
                'url': ''.join(['http://', Site.objects.get_current().domain, product.get_absolute_url()]),
                'image': ''.join(['http://', Site.objects.get_current().domain, product_image]),
                'name': product.manufacturer.name,
                'text': product_price
            })

            count_products = count_products + 1
            used_products.append(product.pk)

        if count_products >= 9:
            break

    product_names = product_names[:5]
    subject = u'%s och andra varumärken i Veckans Bästa!' % (', '.join(product_names),)

    # Looks
    looks = []
    base_looks = list(Look.objects.filter(likes__active=True).annotate(num_likes=Count('likes')).order_by('-num_likes', '-modified')[:4])
    week_looks = list(Look.objects.filter(likes__active=True, likes__modified__gt=one_week_ago).annotate(num_likes=Count('likes')).order_by('-num_likes', '-modified')[:4])

    used_looks = []
    count_looks = 0
    for look in week_looks + base_looks:
        if look.pk not in used_looks:
            static_image = get_thumbnail(look.static_image, '280', crop='noop', modified=str(look.modified)).url
            looks.append({
                'url': ''.join(['http://', Site.objects.get_current().domain, look.get_absolute_url()]),
                'image': ''.join(['http://', Site.objects.get_current().domain, static_image]),
                'name': look.title,
                'user_url': ''.join(['http://', Site.objects.get_current().domain, look.user.get_absolute_url()]),
                'user_name': look.user.get_profile().display_name,
            })

            count_looks = count_looks + 1
            used_looks.append(look.pk)

        if count_looks >= 4:
            break

    # Members
    members = []
    base_members = list(Follow.objects.values_list('object_id', flat=True).annotate(count=Count('id')).order_by('-count')[:4])
    week_members = list(Action.objects.filter(verb='started following', timestamp__gt=one_week_ago)
                                      .values_list('target_object_id', flat=True)
                                      .annotate(count=Count('target_object_id'))
                                      .order_by('-count')[:4])
    
    used_members = []
    count_members = 0
    for member_id in week_members + base_members:
        if member_id not in used_members:
            profile = ApparelProfile.objects.get(user__id=member_id)

            avatar = profile.avatar_medium
            if not avatar.startswith('http://') and not avatar.startswith('https://'):
                avatar = ''.join(['http://', Site.objects.get_current().domain, avatar])

            members.append({
                'url': ''.join(['http://', Site.objects.get_current().domain, profile.get_absolute_url()]),
                'image': avatar,
                'name': profile.display_name,
                'text': u'Följs av %s' % (profile.followers_count,)
            })

            count_members = count_members + 1
            used_members.append(member_id)

        if count_members >= 4:
            break


    if request.GET.get('create'):
        ms = MailSnake(settings.MAILCHIMP_API_KEY)

        batch = []
        for user in User.objects.exclude(Q(email__isnull=True) | Q(email__exact='')).exclude(Q(first_name__isnull=True) | Q(first_name__exact='')).exclude(Q(last_name__isnull=True) | Q(last_name__exact='')):
            batch.append({'EMAIL': user.email, 'FNAME': user.first_name, 'LNAME': user.last_name})

        try:
            ms.listBatchSubscribe(id=settings.MAILCHIMP_WEEKLY_LIST, double_optin=False, update_existing=True, batch=batch)
        except MailSnakeException:
            return HttpResponse('Error: could not update subscribers list')

        template = loader.render_to_string('email/weekly.html', {
            'products': products,
            'products_1': products[0:3],
            'products_2': products[3:6],
            'products_3': products[6:9],
            'looks': looks,
            'members': members,
            'email_weekly_top': request.build_absolute_uri(settings.MEDIA_URL + '/images/weekly-top-sv.gif'),
            'email_weekly_bottom': request.build_absolute_uri(settings.MEDIA_URL + '/images/weekly-bottom-sv.gif'),
            'subject': subject
        })

        options = {
                'list_id': settings.MAILCHIMP_WEEKLY_LIST,
                'subject': subject,
                'from_email': 'postman@apparelrow.com',
                'from_name': 'Apparelrow',
                'to_name': '*|FNAME|*',
                'inline_css': True,
                'generate_text': True
            }

        try:
            result = ms.campaignCreate(type='regular', options=options, content={'html': template})
        except MailSnakeException:
            return HttpResponse('Error: could not create campaign')

        return HttpResponse('Campaign created with id %s' % (result,)) 

    
    return render_to_response('email/weekly.html', {
            'products': products,
            'products_1': products[0:3],
            'products_2': products[3:6],
            'products_3': products[6:9],
            'looks': looks,
            'members': members,
            'email_weekly_top': request.build_absolute_uri(settings.MEDIA_URL + '/images/weekly-top-sv.gif'),
            'email_weekly_bottom': request.build_absolute_uri(settings.MEDIA_URL + '/images/weekly-bottom-sv.gif'),
            'subject': subject
        }, context_instance=RequestContext(request))

#def admin_user_list_extended_csv(request):
    #if not request.user.is_superuser:
        #return HttpResponseNotFound()

    #user_content_type = ContentType.objects.get_for_model(User)
    #one_week_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)

    ## Looks
    #looks = {}
    #looks['U'] = list(Look.objects.annotate(num_likes=Count('likes')).order_by('-num_likes')[:4])
    #looks['M'] = list(Look.objects.filter(gender='M').annotate(num_likes=Count('likes')).order_by('-num_likes')[:4])
    #looks['W'] = list(Look.objects.filter(gender='W').annotate(num_likes=Count('likes')).order_by('-num_likes')[:4])

    ## Products
    #products = {}
    #products['U'] = list(Product.objects.filter(published=True, category__isnull=False)
                                        #.filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                        #.order_by('-popularity')[:6])
    #products['M'] = list(Product.objects.filter(gender='M', published=True, category__isnull=False)
                                        #.filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                        #.order_by('-popularity')[:6])
    #products['W'] = list(Product.objects.filter(gender='W', published=True, category__isnull=False)
                                        #.filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                        #.order_by('-popularity')[:6])

    ## Members
    #members = {'U': [], 'M': [], 'W': []}
    #for object_id in Follow.objects.values_list('object_id', flat=True).annotate(count=Count('id')).order_by('-count'):
        #if len(members['M']) >= 4 and len(members['W']) >= 4 and len(members['U']) >= 4:
            #break

        #profile = ApparelProfile.objects.get(user__id=object_id)
        #if profile.gender not in ['M', 'W']:
            #members['U'].append(profile)
            #members['M'].append(profile)
            #members['W'].append(profile)
        #else:
            #members['U'].append(profile)
            #members[profile.gender].append(profile)

    #csv_string = StringIO.StringIO()
    #writer = csv.writer(csv_string)
    #for user in User.objects.exclude(Q(email__isnull=True) | Q(email__exact='')).exclude(Q(first_name__isnull=True) | Q(first_name__exact='')).exclude(Q(last_name__isnull=True) | Q(last_name__exact='')):
        #profile = user.get_profile()
        #gender = profile.gender
        #if gender not in ['M', 'W']:
            #gender = 'U'

        #user_ids = Follow.objects.filter(content_type=user_content_type, user=user).values_list('object_id', flat=True)
        #user_data = [user.email.encode('utf-8'), user.first_name.encode('utf-8'), user.last_name.encode('utf-8')]

        ## Looks
        #used_looks = []
        #count_looks = 0
        #if gender != 'U':
            #temp_looks = list(Look.objects.filter(likes__user__in=user_ids,
                                                  #likes__active=True,
                                                  #likes__modified__gt=one_week_ago,
                                                  #gender=gender).annotate(num_likes=Count('likes')).order_by('-num_likes')[:4])
        #else:
            #temp_looks = list(Look.objects.filter(likes__user__in=user_ids,
                                                  #likes__active=True,
                                                  #likes__modified__gt=one_week_ago).annotate(num_likes=Count('likes')).order_by('-num_likes')[:4])

        #for look in temp_looks + looks[gender]:
            #if look.pk not in used_looks:
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, look.get_absolute_url()])).encode('utf-8'))
                #user_data.append(u'no-image-yet'.encode('utf-8'))
                #user_data.append(look.title.encode('utf-8'))
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, look.user.get_profile().avatar])).encode('utf-8'))
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, look.user.get_absolute_url()])).encode('utf-8'))
                #user_data.append(look.user.get_profile().display_name.encode('utf-8'))
                #user_data.append((u'Följs av %s' % (look.user.get_profile().followers_count,)).encode('utf-8'))

                #count_looks = count_looks + 1
                #used_looks.append(look.pk)

            #if count_looks >= 4:
                #break

        #looks_length = len(temp_looks + looks[gender])
        #if looks_length < 4:
            #for _ in range(4 - looks_length):
                #user_data.extend(['', '', '', '', '', '', ''])

        ## Products
        #used_products = []
        #count_products = 0
        #if gender != 'U':
            #temp_products = list(Product.objects.filter(likes__user__in=user_ids,
                                                        #likes__active=True,
                                                        #likes__modified__gt=one_week_ago,
                                                        #gender=gender)
                                                #.filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                                #.annotate(num_likes=Count('likes')).order_by('-num_likes')[:6])
        #else:
            #temp_products = list(Product.objects.filter(likes__user__in=user_ids,
                                                        #likes__active=True,
                                                        #likes__modified__gt=one_week_ago)
                                                #.filter(Q(vendorproduct__availability__lt=0) | Q(vendorproduct__availability__gt=0) | Q(vendorproduct__availability__isnull=True))
                                                #.annotate(num_likes=Count('likes')).order_by('-num_likes')[:6])


        #for product in temp_products + products[gender]:
            #if product.pk not in used_products:
                #product_image = get_thumbnail(product.product_image, '176', crop='noop').url
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, product.get_absolute_url()])).encode('utf-8'))
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, product_image])).encode('utf-8'))
                #user_data.append(product.manufacturer.name.encode('utf-8'))
                #user_data.append(u'price stuff'.encode('utf-8'))

                #count_products = count_products + 1
                #used_products.append(product.pk)

            #if count_products >= 6:
                #break

        #products_length = len(temp_products + products[gender])
        #if products_length < 4:
            #for _ in range(4 - products_length):
                #user_data.extend(['', '', '', ''])

        ## Members
        #used_members = []
        #count_members = 0
        #temp_members = []
        #for action in Action.objects.filter(verb='started following', timestamp__gt=one_week_ago, actor_object_id__in=user_ids, actor_content_type=user_content_type):
            #if action.target.get_profile().gender == gender:
                #temp_members.append(action.target.get_profile())

        #for member in temp_members + members[gender]:
            #if member.pk not in used_members:
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, member.get_absolute_url()])).encode('utf-8'))
                #user_data.append((''.join(['http://', Site.objects.get_current().domain, member.avatar_medium])).encode('utf-8'))
                #user_data.append(member.display_name.encode('utf-8'))
                #user_data.append((u'Följs av %s' % (member.followers_count,)).encode('utf-8'))

                #count_members = count_members + 1
                #used_members.append(member.pk)

            #if count_members >= 4:
                #break

        #members_length = len(temp_members + members[gender])
        #if members_length < 4:
            #for _ in range(4 - members_length):
                #user_data.extend(['', '', '', ''])

        #writer.writerow(user_data)

    #response = HttpResponse(csv_string.getvalue(), content_type='text')
    #response['Content-Disposition'] = 'attachment; filename=apparelrow-users.csv'

    #csv_string.close()

    #return response
