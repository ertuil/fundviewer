from typing import List, Optional, Union
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .models import WatchFund
from user.models import Token
from .api import Fund, get_fund, get_price, get_rt_price, get_index
from django.core.cache import cache
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
import logging
# Create your views here.
logger = logging.getLogger("root")


@login_required(login_url='/user/login')
def index(request: HttpRequest):
    user = request.user
    username = user.username

    watch_funds = WatchFund.objects.filter(username=username)

    index_now, china_index, fund_info = get_watch_info(watch_funds)
    return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now})


@login_required(login_url='/user/login')
def fund_view(request: HttpRequest, code: str = None):

    user = request.user
    username = user.username

    if code is None:
        if request.method == 'GET':
            code = request.GET.get('code', None)
        elif request.method == 'POST':
            code = request.POST.get('code', None)
    if code is None:
        return render(request, 'fund_info.html', {'alert': {'type': 'danger', 'content': '请输入基金代码'}})

    fund = get_fund_cache(code)
    if fund is None:
        return render(request, 'fund_info.html', {'alert': {'type': 'danger', 'content': f'基金代码 {code} 未找到'}})

    watch_funds = WatchFund.objects.filter(username=username)
    in_favour = 1
    for wf in watch_funds:
        if wf.fundcode == code:
            in_favour = 2
            break

    fundprice = get_fundprice_cache(code)
    if fundprice is None:
        return render(request, 'fund_info.html', {'alert': {'type': 'danger', 'content': f'基金价格 {code} 查询失败'}, 'fund': fund, 'favour': in_favour})

    try:
        now, fundrt = get_rt_price(fund)
        now = now.strftime("%H:%M")
    except Exception as e:
        logger.error(f"Error getting fund evaluated price {code}: {e}")
        return render(request, 'fund_info.html', {'alert': {'type': 'danger', 'content': '基金估值计算失败'}, 'fund': fund, 'fundprice': fundprice, 'favour': in_favour})
    logger.info(f"evaluate for {code}: {fundrt}")
    fund_rt_show = round(fundrt*100, 2)
    return render(request, 'fund_info.html', {'fund': fund, 'fundprice': fundprice, 'fundrt': fund_rt_show, 'fundrt_now': now, 'favour': in_favour})


def fund_rt_price(request: HttpRequest, code: str = None):
    user: Union[AbstractBaseUser, AnonymousUser] = request.user

    if not user.is_authenticated:
        auth_header = request.headers.get('Authorization', None)
        if auth_header is None:
            return redirect('/user/login')
        try:
            token = auth_header.split()[1]
            tl = Token.objects.filter(token=token)
            if len(tl) == 0:
                return JsonResponse({'status': 'error', 'msg': 'wrong token'}, status=401)
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            return JsonResponse({'status': 'error', 'msg': 'wrong token'}, status=401)

    if code is None:
        if request.method == 'GET':
            code = request.GET.get('code', None)
        elif request.method == 'POST':
            code = request.POST.get('code', None)
    if code is None:
        return JsonResponse({'status': 'error', 'msg': 'error fund code'})

    fund = get_fund_cache(code)
    if fund is None:
        return JsonResponse({'status': 'error', 'msg': 'error getting fund info'})

    try:
        now, fundrt = get_rt_price(fund)
    except Exception as e:
        logger.error(f"Error getting fund {code}: {e}")
        return JsonResponse({'status': 'error', 'msg': 'error getting fund rt price'})
    return JsonResponse({'status': 'ok', 'price': fundrt, 'time': now.strftime("%Y-%m-%d %H:%M:%S")})


@login_required(login_url='/user/login')
def watch_add(request: HttpRequest, code: str = None):
    user = request.user
    username = user.username
    watch_funds = WatchFund.objects.filter(username=username)

    if code is None:
        index_now, china_index, fund_info = get_watch_info(watch_funds)
        return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now, 'alert': {'type': 'danger', 'content': '基金代码错误'}})

    for wf in watch_funds:
        if wf.fundcode == code:
            index_now, china_index, fund_info = get_watch_info(watch_funds)
            return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now, 'alert': {'type': 'warning', 'content': '基金已经存在'}})

    fund = get_fund_cache(code)
    if fund is None:
        index_now, china_index, fund_info = get_watch_info(watch_funds)
        return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now, 'alert': {'type': 'danger', 'content': '获取基金信息失败'}})

    nwf = WatchFund(username=username, fundcode=code, fundname=fund.name)
    nwf.save()

    watch_funds = WatchFund.objects.filter(username=username)
    index_now, china_index, fund_info = get_watch_info(watch_funds)

    return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now, 'alert': {'type': 'success', 'content': '基金添加成功'}})


@login_required(login_url='/user/login')
def watch_del(request: HttpRequest, code: str = None):
    user: Union[AbstractBaseUser, AnonymousUser] = request.user
    username = user.username
    try:
        watch_funds = WatchFund.objects.get(username=username, fundcode=code).delete()
        alert = {'type': 'success', 'content': '基金删除成功'}
    except Exception as e:
        logger.error(f"Error deleting watch fund {code}: {e}")
        alert = {'type': 'danger', 'content': '基金删除失败'}

    watch_funds = WatchFund.objects.filter(username=username)
    index_now, china_index, fund_info = get_watch_info(watch_funds)
    return render(request, 'home.html', {'fund_info': fund_info, 'index': china_index, 'index_now': index_now, 'alert': alert})


def get_fund_cache(code: str) -> Optional[Fund]:
    fund_cache_timeout = 86400 * 15

    key = f"fund-{code}"
    try:
        fund = cache.get(key, default=None)
        if not fund:
            fund = get_fund(code)
            if fund:
                cache.set(key, fund, fund_cache_timeout)
    except Exception as e:
        logger.error(f"error getting fund {code}: {e}")
        return None
    return fund


def get_fundprice_cache(code: str) -> Optional[Fund]:
    fund_cache_timeout = 60*60*24

    key = f"fundprice-{code}"

    try:
        fundprice = cache.get(key, default=None)
        if not fundprice:
            fundprice = get_price(code)
            if fundprice:
                cache.set(key, fundprice, fund_cache_timeout)
    except Exception as e:
        logger.error(f"error getting fund price {code}: {e}")
        return None
    return fundprice


def get_watch_info(watch_funds: List[WatchFund]):
    index_now, china_index = get_index()
    index_now = index_now.strftime("%Y-%m-%d %H:%M:%S")

    fund_info = []
    for wf in watch_funds:
        fund = get_fund_cache(wf.fundcode)
        result = {'code': wf.fundcode, 'name': wf.fundname}

        fundprice = get_fundprice_cache(wf.fundcode)
        if fundprice is None:
            result["unit_price"] = "---"
            result["rate1"] = "---"
        else:
            result["unit_price"] = fundprice.unit_price
            result["rate1"] = round(fundprice.rate1*100, 2)

        if fund is None:
            continue
        try:
            now, fundrt = get_rt_price(fund)
            result["rt_time"] = now.strftime("%H:%M")
            result["rt_rate"] = round(fundrt*100, 2)
        except Exception as e:
            logger.error(f"Error getting fund {wf.fundcode}: {e}")
            result["rt_time"] = "---"
            result["rt_rate"] = "---"
        fund_info.append(result)
    return index_now, china_index, fund_info