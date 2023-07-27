from typing import Union
from django.shortcuts import render, redirect
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
import logging

# Create your views here.

Realm = "fundviewer"
success_redir = "/"
logger = logging.getLogger("root")


def user_login(request: HttpRequest):
    next = request.GET.get("next", success_redir)
    user: Union[AbstractBaseUser, AnonymousUser] = request.user
    if user.is_authenticated:
        return redirect(next)

    if request.method == 'GET':
        return render(request, 'login.html')

    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    if username is None or password is None:
        return render(request, 'login.html', {'alert': {'type': 'danger', 'content': '请输入用户名和密码'}})

    user = authenticate(username=username, password=password)
    if user is not None and user.is_active:
        login(request, user)
        logger.info("User %s logged in", username)
        return redirect(next)

    return render(request, 'login.html', {'alert': {'type': 'danger', 'content': '用户名或密码错误'}})


def user_logout(request: HttpRequest):
    logger.info(f"User {request.user} logged out")
    logout(request)
    return redirect(success_redir)
