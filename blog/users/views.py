from django.shortcuts import render

# Create your views here.
from django.views import View
import re
from django.http.response import HttpResponseBadRequest
from  users.models import User
from django.db import DatabaseError
from django.shortcuts import redirect
from django.urls import reverse
#定义视图层
class RegisterBht(View):
        '''用户注册'''
        def get(self,request):
            '''
            提供注册界面
            :param request: 请求对象
            :return: 注册页面
            '''
            return render(request,"register.html")

        def post(self, request):

            '''
            1、接受数据
            2、验证数据
                2.1参数是否齐全
                2.2手机号格式是否正确
                2.3密码是否符合格式要求
                2.4密码和确认密码要一致
                2.4短信验证码是否和redis中的一致
            3、保存注册信息
            4、返回响应，跳转到指定页面
            :param request:
            :return:
            '''
            #             1、接受数据
            mobile = request.POST.get('mobile')
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            smscode = request.POST.get('sms_code')

            #             2、验证数据
            #                 2.1参数是否齐全
            if not all([mobile, password, password2, smscode]):
                return HttpResponseBadRequest('缺少必要的参数')
            #                 2.2手机号格式是否正确
            if not re.match(r'^1[3-9]\d{9}', mobile):
                return HttpResponseBadRequest('手机号不符合规则')

            #                 2.3密码是否符合格式要求
            if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
                return HttpResponseBadRequest('请输入8-20位密码，密码为数字字母')
            #                 2.4密码和确认密码要一致
            if password != password2:
                return HttpResponseBadRequest('两次密码不一致')
            #                 2.4短信验证码是否和redis中的一致
            redis_conn = get_redis_connection('default')
            redis_sms_code = redis_conn.get('sms:%s' % mobile)
            if redis_sms_code is None:
                return HttpResponseBadRequest('短信验证码已过期')
            if smscode != redis_sms_code.decode():
                return HttpResponseBadRequest('短信验证码不一致')

            #             3、保存注册信息
            # create_user 使用系统的方法来对密码进行加密
            try:
                user = User.objects.create_user(username=mobile,
                                           mobile=mobile,
                                           password=password)
            except DatabaseError as e:
                logger.error(e)
                return  HttpResponseBadRequest('注册失败')

            from django.contrib.auth import login
            login(request,user)
            #             4、返回响应，跳转到指定页面
            # 暂时返回一个注册成功的信息，后期在实现跳转到指定页面
            # redirect 是进行重定向
            # reverse  是可以通过namespace:name来获取到视图所对应的路由
            # 设置coookie信息需要通过response设置，所以将return换成responses

            response = redirect('home:index')
            # return HttpResponse('注册成功，重定向的首页')
            # 设置cookie信息，以方便首页中用户信息展示的判断和用户信息的展示
            response.set_cookie('is_login',True)
            response.set_cookie('username',user.username,max_age=7*24*3600)
            return response

            # 设置cookie信息，以方便首页中，用户信息展示的判断和用户信息的展示
            response.set_cookie('is_login',True)
            response.set_cookie('username',user.username,max_age=7*24*3600)

            return response






from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse


class ImageCodeView(View):
    def get(self, request):

        '''
        1、接受前端传递过来的uuid
        2、判断uuid是否获取到
        3、通过调用captcha来生产图片验证码（图片二进制和图片内容）
        4、将图片内容保存到redis中
            uuid作为key，图片内容作为value，同时还需要设置时效
        5、返回图片二进制
        :param request:
        :return:
        '''
        # 1、接受前端传递过来的uuid
        uuid = request.GET.get('uuid')
        # 2、判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest('没有传递uuid')
        # 3、通过调用captcha来生成图片验证码（图片二进制和图片内容）
        text, image = captcha.generate_captcha()
        # 4、将图片内容保存到redis中的默认库
        redis_conn = get_redis_connection('default')
        # uuid作为key，图片内容作为value，同时还需要设置时效
        # key 设置为uuid
        # seconds 过期秒数， 300秒5分钟过期时间
        # value text
        redis_conn.setex('img:%s' % uuid, 300, text)
        # 5、返回图片二进制
        return HttpResponse(image, content_type='image/jpeg')



from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging
logger =logging.getLogger('django')
from random import randint
from libs.yuntongxun.sms import CCP
class SmsCodeView(View):

    def get(self, request):

        '''
        1、接受参数
        2、参数的验证
            2.1验证参数是否齐全
            2.2图片验证码的验证
                连接redis，获取redis中的图片验证码
                判断图片验证码是否存在
                如果图片验证码未过期，我们获取到之后就可以删除图片验证码
                比对图片验证码
        3、生成短信验证码
        4、保存短信验证码到redis中
        5、发送短信
        6、返回响应
        :param request:
        :return:
        '''

        #  1、接受参数（查询字符串的形式传递过来）
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        #         2、参数的验证
        #             2.1验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必要的参数'})
        #             2.2图片验证码的验证
        #                 连接redis，获取redis中的图片验证码
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img:%s' % uuid)
        #                 判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码已过期'})
        #                 如果图片验证码未过期，我们获取到之后就可以删除图片验证码
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)
        #                 比对图片验证码,注意大小写问题，redis的数据是bytes类型
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码错误'})
        #         3、生成短信验证码
        sms_code = '%06d' % randint(0, 999999)
        # 为了后期比对方便，我们可以将短信验证码记录到日志中
        logger.info(sms_code)
        #         4、保存短信验证码到redis中
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        #         5、发送短信
        CCP().send_template_sms(mobile, [sms_code, 5], 1)
        #         6、返回响应
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功'})

class LoginBht(View):
    def get(self,request):
        '''
        提供登陆页面
        1、接收参数
        2、参数的验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3、用户认证登陆
        4、状态的保持
        5、根据用户选择的是否记住登录状态来进行判断
        6、为了首页显示我们需要设置一些cookie信息
        7、返回响应
        :param request:请求对象
        :return: 登陆页面
        '''
        return render(request,'login.html')
    def post(self,request):
        # 提供登陆页面
        # 1、接收参数
        # 2、参数的验证
        #     2.1验证手机号是否符合规则
        #     2.2验证密码是否符合规则
        # 3、用户认证登陆
        # 4、状态的保持
        # 5、根据用户选择的是否记住登录状态来进行判断
        # 6、为了首页显示我们需要设置一些cookie信息
        # 7、返回响应
        # :param request:请求对象
        # :return: 登陆页面
        # 1、接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2、参数的验证
        #     2.1验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.2验证密码是否符合规则
        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规范')
        # 3、用户认证登陆
        # 采用系统自带的认证方法进行人证
        # 如果我们的用户名和密码正确，返回user
        # 如果我们的用户名或密码不正确，会返回None
        from django.contrib.auth import authenticate
        # 默认的认证方法是针对于username字段进行用户名的判断
        # 当前的判断信息是手机号，所以我们需要修改一下认证字段
        # 我们需要到User模型中进行修改，等测试出现问题我们在修改
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')


        # 4、状态的保持
        from django.contrib.auth import login
        login(request, user)
        # 5、根据用户选择的是否记住登录状态来进行判断
        # 6、为了首页显示我们需要设置一些cookie信息

        # 根据next参数来进行页面的跳转
        next_page =request.GET.get('next')
        if next_page:
            response =redirect(next_page)
        else:
            response = redirect(reverse('home:index'))
        if remember != 'on':  # 没有记住用户信息
            # 浏览器关闭之后
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=14*24*3600)
        else:        # 记住用户信息
            # 默认记住2周
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14*24*3600)
            response.set_cookie('username', user.username, max_age=14*24*3600)

        # 7、返回响应
        return response


from  django.contrib.auth import logout
class LogoutView(View):
    def get(self, request):
        # 1、session数据清除
        logout(request)
        # 2、删除部分cookie数据
        response = redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        # 3、跳转到首页
        return response


class ForgetPasswordView(View):
    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        '''
        1、接受数据
        2、验证数据
            2.1判断参数是否齐全
            2.2手机号是否符合规则
            2.3判断密码是否符合规则
            2.4判断确认页密码和密码是否一致
            2.5判断短信验证码是否正确
        3、根据手机号进行用户信息的查询
        4、如果手机号查询出用户信息则进行用户密码的修改
        5、如果手机号没有查询出用户信息，则进行新用户的创建
        6、进行页面跳转，跳转到登陆页面
        :param request:
        :return:
        '''
        # 1、接受数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2、验证数据
        #     2.1判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('参数不全')
        #     2.2手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return  HttpResponseBadRequest('手机号不符合规则')
        #     2.3判断密码是否符合规则
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规范')

        #     2.4判断确认页密码和密码是否一致
        if password2 != password:
            return HttpResponseBadRequest('密码不一致')
        #     2.5判断短信验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() != smscode:
            return HttpResponseBadRequest('短信验证码错误')
        # 3、根据手机号进行用户信息的查询
        try:
            user =User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 5、如果手机号没有查询出用户信息，则进行新用户的创建
            try:
                User.objects.create_user(username=mobile,
                                         mobile=mobile,
                                         password=password)
            except Exception:
                return HttpResponseBadRequest("修改失败请稍后再试")

        else:
            # 4、如果手机号查询出用户信息则进行用户密码的修改
            user.set_password(password)
            user.save()


        # 6、进行页面跳转，跳转到登陆页面
        response = redirect(reverse('users:login'))
        return response

from  django.contrib.auth.mixins import LoginRequiredMixin
# 如果用户未登陆的话，则会进行默认的跳转
# 默认的跳转连接是：account/login/?next=xxxx
class UserCenterView(LoginRequiredMixin,View):
    def get(self, request):
        # 获取登陆用户的信息
        user = request.user
        # 组织获取用户的信息
        context = {
           'username': user.username,
           'mobile': user.mobile,
           'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context=context)
    def post(self,request):
        '''
        1、接受参数
        2、将参数保存起来
        3、更新cookie中的username信息
        4、刷新当前页面
        5、返回响应
        :param request:
        :return:
        '''
        # 1、接受参数
        user =request.user
        username =request.POST.get('username',user.username)
        user_desc =request.POST.get('desc',user.user_desc)
        avatar =request.FILES.get('avatar')
        # 2、将参数保存起来
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()

        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改是不，请稍后再试')

        # 3、更新cookie中的username信息

        # 4、刷新当前页面
        response = redirect(reverse('users:center'))
        response.set_cookie('username',user.username,max_age=14*3600*24)
        # 5、返回响应
        return response

from  home.models import ArticleCategory
from home.models import ArticleCategory,Article
class WriteBlogView(LoginRequiredMixin,View):
    def get(self, request):
        # 查询所有分类模型
        categories =ArticleCategory.objects.all()
        context ={
            'categories' :categories
        }

        return render(request,'write_blog.html',context=context)

    def post(self, request):
        '''
        1、接受数据
        2、验证数据
        3、数据入库
        4、跳转到指定界面
        :param request:
        :return:
        '''
        # 1、接受数据
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        summary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        # 2、验证数据
        # 2.1验证数据是否齐全
        if not all([avatar, title, category_id, tags, summary, content]):
            return HttpResponseBadRequest('参数不齐全')
        # 2.2判断分类id
        try:

            article_category = ArticleCategory.objects.get(id =category_id)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('没有此分类')

        # 3、数据入库
        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                tags=tags,
                title =title,
                summary=summary,
                content=content
            )

        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后重试')

        # 4、跳转到指定界面
        return redirect(reverse('home:index'))