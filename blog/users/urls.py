# -*- coding: utf-8 -*-
# @Time    : 2021/3/13 23:01
# @Author  : baht
# @FileName: urls
# @Software: PyCharm
# @project: blog

# 进行users的子路由设置

# 定义访问路径与处理器的映射关系
from django.urls import path
from users.views import RegisterBht, LoginBht

urlpatterns = [
    path("register/",RegisterBht.as_view()),
    path('login/',LoginBht.as_view())
]