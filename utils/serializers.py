#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/6/7 16:10
# @Author  : payne
# @File    : serializers.py
# @Description :

from rest_framework import serializers


class QuestionsSetManageSerializer(serializers.Serializer):
    industry_id = serializers.CharField(required=True)
    occu_id = serializers.CharField(required=False)
    sub_occu_id = serializers.CharField(required=False)
    emp_duration_id = serializers.CharField(required=False)
    expertise_level_id = serializers.CharField(required=False)
    module_id = serializers.CharField(required=True)
    page_count = serializers.IntegerField(required=False)
    page_index = serializers.IntegerField(required=False)

    def validate(self, data):
        # 自定义参数验证逻辑
        # 这里可以对参数进行额外的验证操作
        return data
