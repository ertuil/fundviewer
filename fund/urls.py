from django.urls import path
from .views import index, fund_view, fund_rt_price, watch_add, watch_del

urlpatterns = [
    path('', index, name='index'),
    path('fund', fund_view, name='fund_view'),
    path('fund/<code>', fund_view, name='fund_view_2'),
    path('rt', fund_rt_price, name='fund_rt_view'),
    path('rt/<code>', fund_rt_price, name='fund_rt_view_2'),
    path('watch/add/<code>', watch_add, name='watch_add'),
    path('watch/del/<code>', watch_del, name='watch_del'),
]
