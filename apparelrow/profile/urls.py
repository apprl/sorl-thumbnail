from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from apparelrow.profile.views import ProfileView, ProfileListLookView, ProfileListLikedLookView, \
    ProfileListBrandLookView, ProfileListShopView, ProfileListFollowersView, ProfileListFollowingView, \
    UserSettingsEmailView, UserSettingsNotificationView, PublisherSettingsNotificationView, RedirectProfileView

urlpatterns = patterns('',
    url(r'^flow/$', 'apparelrow.profile.views.flow', name='login-flow-redirect'),
    url(r'^settings/$', RedirectView.as_view(url=reverse_lazy('settings-account')), name='settings-email'),
    url(r'^settings/account/$', UserSettingsEmailView.as_view(), name='settings-account'),
    url(r'^settings/notifications/$', UserSettingsNotificationView.as_view(), name='settings-notifications'),

    url(r'^notifications/$', 'apparelrow.profile.views.notifications' , name='notifications-page'),
    url(r'^settings/publisher/$', PublisherSettingsNotificationView.as_view(), name='settings-publisher'),
    url(r'^settings/description/$', 'apparelrow.profile.views.save_description', name='settings-save-description'),
    url(r'^confirm/email/$', 'apparelrow.profile.views.confirm_email', name='user-confirm-email'),
    url(r'^welcome/$', 'apparelrow.profile.views.login_flow_brands', name='login-flow-brands'),
    url(r'^welcome/complete/$', 'apparelrow.profile.views.login_flow_complete', name='login-flow-complete'),
    url(r'^(?:([^\/]+?)/)?$', RedirectProfileView.as_view(), name='profile-default'),
    url(r'^(?:([^\/]+?)/)?items/$', ProfileView.as_view(template_name='profile/likes.html'), name='profile-likes'),
    url(r'^(?:([^\/]+?)/)?updates/$', RedirectView.as_view(url=reverse_lazy('profile-likes')), name='redirect-profile-updates'),
    url(r'^(?:([^\/]+?)/)?looks/$', ProfileListLookView.as_view(), name='profile-looks'),
    #url(r'^(?:([^\/]+?)/)?looks/$', 'apparelrow.profile.views.looks', name='profile-looks'),
    #url(r'^(?:([^\/]+?)/)?likedlooks/$', 'apparelrow.profile.views.likedlooks', name='profile-likedlooks'),
    url(r'^(?:([^\/]+?)/)?likedlooks/$', ProfileListLikedLookView.as_view(), name='profile-likedlooks'),
    #url(r'^(?:([^\/]+?)/)?brandlooks/$', 'apparelrow.profile.views.brandlooks', name='profile-brandlooks'),
    url(r'^(?:([^\/]+?)/)?brandlooks/$', ProfileListBrandLookView.as_view(), name='profile-brandlooks'),

    #url(r'^(?:([^\/]+?)/)?shops/$', 'apparelrow.profile.views.shops', name='profile-shops'),
    url(r'^(?:([^\/]+?)/)?shops/$', ProfileListShopView.as_view(), name='profile-shops'),
    #url(r'^(?:([^\/]+?)/)?followers/$', 'apparelrow.profile.views.followers', name='profile-followers'),
    url(r'^(?:([^\/]+?)/)?followers/$', ProfileListFollowersView.as_view(), name='profile-followers'),
    #url(r'^(?:([^\/]+?)/)?following/$', 'apparelrow.profile.views.following', name='profile-following'),
    url(r'^(?:([^\/]+?)/)?following/$', ProfileListFollowingView.as_view(), name='profile-following'),
    url(r'^login/(?P<user_id>\d+)/$', 'apparelrow.profile.views.login_as_user', name='login-as-user'),
)