from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from django.conf.urls import url

from pool_ladder.consumers import MainConsumer, NotificationConsumer

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter([
            url(r'^pool-ladder/$', MainConsumer)
        ])
    ),
    'channel': ChannelNameRouter({
        'notifications': NotificationConsumer
    }),
})
