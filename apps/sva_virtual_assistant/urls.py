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
        "user_models_content/",
        views.UQDUserQuestionDetailsContent.as_view(),
        name="用户自建模型内容详情",
    ),
    path(
        "user_models/",
        views.UQDUserQuestionDetailsView.as_view(),
        name="用户自建模型列表"),
    path(
        "remote_dict/",
        views.RemoteDictView.as_view(),
        name="获取远程字典"),
    path(
        "sva_me/",
        views.SvaMeList.as_view(),
        name="获取主形象"),
    path(
        "sva_tutor/",
        views.SvaTutorList.as_view(),
        name="获取关联形象"),
    path(
        "regions/",
        views.GetRegion.as_view(),
        name="获取地区"),
    path(
        "batch_me_tutor/",
        views.BatchGetTutorMe.as_view(),
        name="批量获取导师和我"),
    path(
        "batch_bind_tutor/",
        views.BatchBindTutor.as_view(),
        name="批量绑定导师"),
    path(
        "prompt/",
        views.PromptManage.as_view(),
        name="提示词"),
    path(
        "match_context/",
        views.MatchContext.as_view(),
        name="获取上下文"),
]
