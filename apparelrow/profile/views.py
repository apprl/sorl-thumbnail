import logging
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext
from django.db import connection
from django.views.generic import list_detail

from apparel.decorators import get_current_user
from apparel.models import *
from apparel.forms import *
from voting.models import Vote
from actstream.models import actor_stream



@get_current_user
def profile(request, profile):
    """
    Displays the profile page
    """
    
    context = {
        "profile": profile,
        'updates': actor_stream(profile.user)[:10],
        'recent_looks': Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        #'recent_likes': recent_likes
    }
    
    return render_to_response('profile/profile.html', context, context_instance=RequestContext(request))


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
