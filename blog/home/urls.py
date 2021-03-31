# -*- coding: utf-8 -*-
# @Time    : 2021/3/17 18:52
# @Author  : baht
# @FileName: urls.py
# @Software: PyCharm
# @project: blog

from django.urls import path
from home.views import IndexView
from home.views import DetailView
urlpatterns =[
    # 首页路由
    path('', IndexView.as_view(), name='index'),
    # 详情路由
    path('detail/', DetailView.as_view(), name='detail'),
]