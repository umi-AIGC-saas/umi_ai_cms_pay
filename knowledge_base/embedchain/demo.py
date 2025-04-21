#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/12/26 17:52
# @Author  : payne
# @File    : demo.py
# @Description :
# import os
#
from pipeline import Pipeline as App
#

# import requests
# requests.packages.urllib3.disable_warnings()
# # https://api.openai.com/v1/
# # https://openai.qiheweb.com/v1
# os.environ["OPENAI_API_KEY"] = "sk-aWlXvBleYj9FiZZ176A4B2Be9aBc4dBcA70a0d498eFf7e18"
# os.environ["OPENAI_BASE_URL"] = "https://openai.qiheweb.com/v1"
#
# # app = App.from_config(config_path="configs/full-stack.yaml")
# app = App.from_config(config_path="configs/opensearch.yaml")
# app.reset()

# Embed online resources
# app.add("https://en.wikipedia.org/wiki/Elon_Musk")
# app.add("https://www.forbes.com/profile/elon-musk")
# exist = app.db.get(where={'agent_id': "199986", "user_id": 10087, "file_id": 1231})
# print(exist)
# print("existexistexistexist")


# app.add('https://umi-intelligence.oss-cn-shenzhen.aliyuncs.com/0/节选.pdf', metadata={'agent_id': "199987", 'user_id': 10086})
# app.add('https://umi-intelligence.oss-cn-shenzhen.aliyuncs.com/0/我没死.pdf', metadata={'agent_id': "199986", "user_id": 10087, "file_id": 1231})
# app.add('/Users/panjie/Downloads/节选.pdf',  metadata={'app_label': '节选', 'doc_id': "199987", 'user_id': 10086, 'company_id': 1})
# app.add('/Users/panjie/Downloads/我没死.pdf',  metadata={'app_label': '我没死', 'doc_id': "199986", 'user_id': 10087, 'company_id': 2})
#
# app.add('/Users/panjie/Downloads/节选.pdf', metadata={'company_id':1, 'user_id': 10086, 'file_id': '9897877686876', 'file_name': '节选.pdf'} )
# app.add('/Users/panjie/Downloads/我没死.pdf',metadata={'company_id':2, 'user_id': 10087, 'file_id': '9897877686877', 'file_name': '我没死.pdf'} )


# bot = app
#
# asnwer = app.query("根据为什么唐⼤夫不能来了扩写文章 ", citations=True, where={'user_id': 10087, 'company_id': 2})
# print(asnwer)
# #




