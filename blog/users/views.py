from django.shortcuts import render

# Create your views here.
from django.views import View
import re
from django.http.response import HttpResponseBadRequest
from  users.models import User
from django.db import DatabaseError
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
            #             4、返回响应，跳转到指定页面
            # 暂时返回一个注册成功的信息，后期在实现跳转到指定页面
            return HttpResponse('注册成功，重定向的首页')



class LoginBht(View):
    def get(self,request):
        '''
        提供登陆页面
        :param request:请求对象
        :return: 登陆页面
        '''
        return render(request,'login.html')


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
        redis_image_code = redis_conn.get('img:%s'%uuid)
        #                 判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码已过期'})
        #                 如果图片验证码未过期，我们获取到之后就可以删除图片验证码
        try:
            redis_conn.delete('img:%s'%uuid)
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
