from django.shortcuts import render

# Create your views here.
from django.views import View


class RegisterBht(View):
        def get(self,request):
            return render(request,"register.html")

class LoginBht(View):
    def get(self,request):
        return render(request,'login.html')