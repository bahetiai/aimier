# -*- coding: utf-8 -*-
# @Time    : 2021/3/13 23:01
# @Author  : baht
# @FileName: urls
# @Software: PyCharm
# @project: blog

# 进行users的子路由设置
# 定义访问路径与处理器的映射关系
from django.urls import path
from users.views import RegisterBht
from users.views import LoginBht
from users.views import ImageCodeView
from users.views import SmsCodeView
from users.views import LogoutView
from users.views import ForgetPasswordView
from users.views import UserCenterView
urlpatterns = [
    # 参数1：路由
    # 参数2：视图函数
    # 参数3：方便通过reverse来获取路由
    path("register/", RegisterBht.as_view(), name ='register'),
    # 登陆路由
    path('login/', LoginBht.as_view(), name='login'),
    # 退出登录
    path('logout/', LogoutView.as_view(), name='logout'),
    # 忘记密码
    path('forgetpassword/', ForgetPasswordView.as_view(), name='forgetpassword'),
    # 图片验证码路由
    path('imagecode/', ImageCodeView.as_view()),
    # 短信发送
    path('smscode/', SmsCodeView.as_view()),

    # 用户中心
    path('center/',UserCenterView.as_view(),name ='center'),

]