from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse

from fund.views import fund_rt_price

# Create your views here.


def api_rt(request: HttpRequest, code: str = None):
    print(1)
    return redirect(reverse(fund_rt_price, args=[code]))