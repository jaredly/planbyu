from django.conf.urls import patterns, include, url

import views 

urlpatterns = patterns(
    '',
)

urlpatterns += views.route.get_patterns()


# vim: et sw=4 sts=4
