import re

from django.http import QueryDict


class ValidateParamsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        return self.process_response(response)

    def process_request(self, request):
        # 处理 POST 和 PUT 请求
        if request.method in ["POST", "PUT"]:
            request_data = (request.data if request.method ==
                            "POST" else QueryDict(request.body))
            mutable_data = request_data.copy()  # 创建可变副本
            for key, value in mutable_data.items():
                # 去除空格
                value = value.strip()
                # 更新请求参数
                mutable_data[key] = value  # 更新可变副本

                request.data = mutable_data
        elif request.method in ["DELETE", "GET", "PATCH"]:
            mutable_data = request.GET.copy()
            for key, value in mutable_data.items():
                # 去除空格
                value = value.strip()
                # 更新请求参数
                mutable_data[key] = value  # 更新可变副本
            request.GET = mutable_data

    def process_response(self, response):
        # 对响应进行处理
        return response
