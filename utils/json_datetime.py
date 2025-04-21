#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/5/21 00:50
# @Author  : payne
# @File    : json_datetime.py
# @Description :


import json
from datetime import datetime


# 自定义 JSON 编码器
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # 将 datetime 对象转换为字符串，格式为 ISO 8601
            return obj.isoformat()
        return super().default(obj)
