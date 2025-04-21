#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 11:53
# @Author  : payne
# @File    : urls.py
# @Description : pay 模块路由


from django.urls import path

from . import views

urlpatterns = [
    path(
        "upload_document/",
        views.UploadFileToSpark.as_view(),
        name="上传知识库文档-文档对话"),
    path(
        "match_context_kb/",
        views.MatchContextSpark.as_view(),
        name="匹配星火知识库回答-文档对话"),
]
