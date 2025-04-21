#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/12/28 15:37
# @Author  : payne
# @File    : search.py
# @Description :


from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=['https://localhost:9200']
)

# https://localhost:9200
response = client.search(
    index="my-app",
    body={"query": {"match_all": {}}}
)

print(response)
