import logging
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext
from django.db import connection

from apparel.decorators import seamless_request_handling
from apparel.models import *
from apparel.forms import *
from voting.models import Vote
from actstream.models import actor_stream




def profile(request):
    """
    Displays the profile page
    """
    user = request.user
    
    context = {
        'updates': actor_stream(user)[:10],
        'recent_looks': Look.objects.filter(user=user).order_by('-modified')[:4],
        #'recent_likes': recent_likes
    }
    
    return render_to_response('profile/profile.html', context, context_instance=RequestContext(request))


def looks(request):
    
    user = request.user
    
    context = {
        'looks': Look.objects.filter(user=user).order_by('-modified'),
        'popular_looks': get_top_looks(user, 10)
    }
    
    return render_to_response('profile/looks.html', context, context_instance=RequestContext(request))




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
