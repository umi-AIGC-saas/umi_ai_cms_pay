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
        "pictures/",
        views.AgentPictures.as_view(),
        name="智能体图片管理"),
    path(
        "documents/",
        views.AgentDocuments.as_view(),
        name="智能体文档管理"),
    path(
        "websites/",
        views.AgentUrls.as_view(),
        name="智能体网络地址管理"),
    path(
        "models/",
        views.AgentModels.as_view(),
        name="智能体管理"),
    path(
        "agent_group_edit/",
        views.AgentGroupEdit.as_view(),
        name="智能体分组修改"),
    path(
        "groups/",
        views.Groups.as_view(),
        name="获取用户下所有的分组树状图"),
    path(
        "agent_groups/",
        views.AgentGroups.as_view(),
        name="获取用户下所有的智能体树状图"),
    path(
        "groups_model/",
        views.AgenClassificationGroup.as_view(),
        name="获取用户模型下所有的分组和分类树状图"),
    path(
        "chat/",
        views.AgentChat.as_view(),
        name="模型对话"),
]
