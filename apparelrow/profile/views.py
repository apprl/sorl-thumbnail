import logging
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext
from django.db import connection
from django.views.generic import list_detail
from django.contrib.contenttypes.models import ContentType

from apparel.decorators import get_current_user
from apparel.models import *
from apparel.forms import *
from voting.models import Vote
from actstream.models import user_stream, actor_stream, Follow


@get_current_user
def home(request, profile, page=0):
    """
    Displays the logged in user's page
    """
    queryset = user_stream(request.user)
    
    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/profile.html",
        paginate_by=10,
        page=page,
        extra_context={
            "profile": profile,
            "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
            "facebook_friends": get_facebook_friends(request)
        }
    )

@get_current_user
def profile(request, profile, page=0):
    """
    Displays the profile page
    """
    queryset = actor_stream(profile.user)
    
    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/profile.html",
        paginate_by=10,
        page=page,
        extra_context={
            "profile": profile,
            "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }
    )


@get_current_user
def looks(request, profile, page=0):
    queryset = Look.objects.filter(user=profile.user).order_by('-modified')
    popular  = get_top_looks(profile.user, 10)
    
    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name='profile/looks.html',
        paginate_by=10,
        page=page,
        extra_context={
            "profile": profile,
            "popular_looks": popular
            # FIXME: Add the most used brand to display in the left column
        }
    )
    
@get_current_user
def followers(request, profile, page=0):
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, object_id=profile.user.id)

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/followers.html",
        paginate_by=10,
        page=page,
        extra_context={
            "profile": profile
        }
    )

@get_current_user
def following(request, profile, page=0):
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, user=profile.user)

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/following.html",
        paginate_by=10,
        page=page,
        extra_context={
            "profile": profile
        }
    )

def get_facebook_friends(request):
    if request.facebook:
        friends = request.facebook.graph.get_connections('me', 'friends')
        friends_uids = [f.uid for f in friends]
        FacebookProfile.objects.filter(uid__in=friends_uids)

def get_top_looks(user, limit=10):
    """
    Returns a list of objects for the most popular looks for the given user.
    """
    
    # FIXME: This needs the following refactoring
    #  - Make work with any model, not just Look
    #  - Support other databases than MySQL
    #  - Return dictionary rather than objects
    
    query = """
        SELECT 
            v.object_id, 
            SUM(v.vote) AS score
        FROM 
            %s AS v,
            %s AS l
        WHERE
                v.object_id = l.id
            AND l.user_id = %%s
        GROUP BY v.object_id
        ORDER BY score DESC
        LIMIT %%s
    """ % (
            connection.ops.quote_name(Vote._meta.db_table),
            connection.ops.quote_name(Look._meta.db_table)
    )
    cursor = connection.cursor()
    cursor.execute(query, [user.id, limit])
    objects = Look.objects.in_bulk([id for id, score in cursor.fetchall()])
    
    return objects.values()
