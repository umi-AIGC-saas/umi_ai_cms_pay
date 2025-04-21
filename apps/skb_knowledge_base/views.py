import ast
import json
import logging
import os
import ssl
import time
import traceback

import requests
import websocket
from django.conf import settings
from django.db import connection, connections
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.views import APIView

from language.language_pack import RET, Language
from utils.cst_class import CstException, CstResponse
from utils.gadgets import gadgets
from utils.spark_utils import (DocumentUpload, SparkQA)
from utils.sql_oper import MysqlOper

logger = logging.getLogger("view")


class UploadFileToSpark(APIView):
    @swagger_auto_schema(
        operation_id="130",
        tags=["V5.6"],
        operation_summary="上传文件",
        operation_description="上传文件到星火的知识库",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["file_url", "file_name"],
            properties={
                "file_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文件网络地址"
                ),
                "file_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文件名称"
                ),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户id"),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT, properties={}
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Invalid request parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        data = request.data
        file_url = data.get("file_url")
        file_name = data.get("file_name")
        user_id = data.get("user_id")

        if not file_url or not file_name or not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        file_type = file_name.split(".")[-1]

        print(file_name)
        print(file_type)
        if file_type.lower() not in ["doc", "docx", "pdf", "md", "txt"]:
            code = RET.UNSUPPORTED_FILE
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        save_path = f"static/{file_name}"
        try:

            print(file_url)
            print(save_path)
            gadgets.download_file(settings.OSS_PREFIX + file_url, save_path)
        except Exception:
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        try:
            pages = gadgets.count_pages(save_path, file_type)

            if pages <= 0:
                code = RET.UNSUPPORTED_FILE
                message = Language.get(code)
                return CstResponse(code=code, message=message)

        except Exception:
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        curTime = str(int(time.time()))
        request_url = "https://chatdoc.xfyun.cn/openapi/fileUpload"

        document_upload = DocumentUpload(curTime)
        headers = document_upload.get_header()

        print(333333)
        # Submit network file
        full_file_url = settings.OSS_PREFIX + file_url
        body = document_upload.get_body(full_file_url, file_name)
        headers["Content-Type"] = body.content_type
        response = requests.post(request_url, data=body, headers=headers)
        res_data = json.loads(response.text)

        print(res_data)
        if not res_data.get("flag"):
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        file_id = res_data.get("data", {}).get("fileId")
        # Submit local file
        # files, body = document_upload.get_files_and_body()
        # response = requests.post(request_url, files=files, data=body, headers=headers)

        sql_insert_db = (
            f"INSERT INTO {settings.DEFAULT_DB}.skb_knowledge_file (user_id, file_url, file_name, file_id) VALUES  "
            f"(%s,%s, %s,%s)")

        params = [user_id, file_url, file_name, file_id]

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert_db, params)
                if cursor.rowcount > 0:

                    consume_hashrate = gadgets.operate_hashrates(
                        user_id=user_id, hashrate=6 * pages
                    )

                    if consume_hashrate:
                        code = RET.OK
                        message = Language.get(code)
                        ret_message = {
                            "file_name": file_name, "file_id": file_id}
                        os.remove(save_path)
                        return CstResponse(
                            code=code, message=message, data=ret_message)
                    else:
                        code = RET.ERROR_CONSUME_HASHRATE
                        message = Language.get(code)
                        return CstResponse(code=code, message=message)
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="119",
        tags=["V5.6"],
        operation_summary="获取用户文件信息",
        operation_description="根据用户ID获取该用户在知识库中的文件信息",
        manual_parameters=[
            openapi.Parameter(
                "file_id",
                openapi.IN_QUERY,
                description="文件 id",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="响应码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="响应消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户ID"
                                    ),
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件网络地址"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件名称"
                                    ),
                                    "file_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件ID"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        file_id = request.query_params.get("file_id")
        sql_query = (
            f"SELECT user_id, file_url, file_name, file_id FROM {settings.DEFAULT_DB}.skb_knowledge_file WHERE "
            f"file_id = %s AND is_delete = 0 ")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query, [file_id])
                results = MysqlOper.get_query_result(cursor)

                ret_data = []
                for row in results:
                    row_dict = {}
                    user_id = row.get("user_id")
                    file_url = row.get("file_url")
                    file_name = row.get("file_name")
                    file_id = row.get("file_id")
                    row_dict["user_id"] = user_id
                    row_dict["file_url"] = file_url
                    row_dict["file_name"] = file_name
                    row_dict["file_id"] = file_id
                    ret_data.append(row_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="127",
        tags=["V5.6"],
        operation_summary="删除用户文件",
        operation_description="根据文件ID和用户ID标记用户文件为已删除",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "file_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "file_id": openapi.Schema(type=openapi.TYPE_STRING, description="文件ID"),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="响应码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="响应消息"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def delete(self, request):
        user_id = request.data.get("user_id")
        file_id = request.data.get("file_id")
        try:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.skb_knowledge_file SET is_delete = 1 WHERE file_id = %s "
                f"AND user_id = %s")

            with connection.cursor() as cursor:
                cursor.execute(sql_delete, [file_id, user_id])
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class MatchContextSpark(APIView):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.ret_message = []

    @swagger_auto_schema(
        operation_id="122",
        tags=["V5.6"],
        operation_summary="提交问题并获取答案",
        operation_description="提交一个问题，并利用文档知识库获取相关的答案",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["file_id", "question_content"],
            properties={
                "file_id": openapi.Schema(type=openapi.TYPE_STRING, description="文件ID"),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="user_id"
                ),
                "question_content": openapi.Schema(
                    type=openapi.TYPE_STRING, description="问题内容"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="响应码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="响应消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "prompt": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="提示信息"
                                ),
                            },
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data
        file_id = data.get("file_id")
        user_id = data.get("user_id")
        question_content = data.get("question_content")
        curTime = str(int(time.time()))
        OriginUrl = "wss://chatdoc.xfyun.cn/openapi/chat"
        document_Q_And_A = SparkQA(curTime, OriginUrl)

        wsUrl = document_Q_And_A.get_url()
        body = document_Q_And_A.get_body(
            file_id=file_id, question=question_content)

        # 禁用WebSocket库的跟踪功能，使其不再输出详细的调试信息。
        websocket.enableTrace(False)

        ws = websocket.WebSocketApp(
            wsUrl,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        ws.appid = settings.SPARK_KNOWLEDGE_BASE_APP_ID
        ws.question = body
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        try:
            gadgets.operate_hashrates(user_id=user_id, hashrate=18)
        except Exception:
            code = RET.ERROR_CONSUME_HASHRATE
            message = Language.get(code)
            raise CstException(code=code, message=message)

        code = RET.OK
        message = Language.get(code)
        ret_dict_message = {
            "prompt": f"请将以下内容作为已知信息：\n【{''.join(self.ret_message)}】。\n 请根据以上内容回答用户的问题。如果已知信息是空，请回答："
            f"抱歉，在文档中没有找到与提问相关的内容，请尝试换个问题问问吧。如果已知信息不为空,则将已知信息返回即可, 不要联想也不要自由发挥. ", }
        return CstResponse(data=ret_dict_message, code=code, message=message)

    # 收到websocket错误的处理
    def on_error(self, ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(self, ws, close_status_code, close_msg):
        print("### closed ###")
        print("关闭代码：", close_status_code)
        print("关闭原因：", close_msg)

    # 收到websocket连接建立的处理
    def on_open(self, ws):
        data = json.dumps(ws.question)
        ws.send(data)

    # 收到websocket消息的处理
    def on_message(self, ws, message):
        data = json.loads(message)
        code = data["code"]
        if code != 0:
            print(f"请求错误: {code}, {data}")
            ws.close()
        else:
            content = data["content"]
            status = data["status"]
            self.ret_message.append(content)
            print(content, end="")
            if status == 2:
                ws.close()

