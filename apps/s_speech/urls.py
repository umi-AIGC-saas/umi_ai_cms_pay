#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 11:53
# @Author  : payne
# @File    : urls.py
# @Description : pay 模块路由


from django.urls import path

from . import views

urlpatterns = [
    path("speech_to_text/", views.SpeechToText.as_view(), name="语音对讲,转录文字"),
    path("text_to_speech/", views.TextToSpeech.as_view(), name="语音对讲, 转录语音"),
]
