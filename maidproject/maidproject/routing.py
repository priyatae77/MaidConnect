from django.urls import re_path
from maidapp import consumers

websocket_urlpatterns = [
    re_path(r'ws/status/$', consumers.StatusConsumer.as_asgi()),
]
