# -*- coding: utf-8 -*-
# @Time    : 2021/3/17 18:52
# @Author  : baht
# @FileName: urls.py
# @Software: PyCharm
# @project: blog

from django.urls import path
from home.views import IndexView
urlpatterns =[
    #首页路由
    path('index/', IndexView.as_view(), name='index'),
]