import json
import logging
import time
import traceback
from collections import defaultdict
from django.conf import settings
from django.db import connection, connections, transaction
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.views import APIView

from language.language_pack import RET, Language
from utils.cst_class import CstException, CstResponse
from utils.distributed_id_generator.get_id import get_distributed_id
from utils.prompts import generate_structured_prompt_agent
from utils.sql_oper import MysqlOper

logger = logging.getLogger("view")


class AgentPictures(APIView):
    worker_id = 8888

    @swagger_auto_schema(
        operation_id="200",
        tags=["智能体"],
        operation_summary="智能体图片管理",
        operation_description="智能体图片管理",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["group_name", "pic_name", "pic_url", "user_id", "group_order"],
            properties={
                "group_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组名称"
                ),
                "pic_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="图片后缀名称"
                ),
                "pic_url": openapi.Schema(type=openapi.TYPE_STRING, description="图片地址"),
                "pic_tags": openapi.Schema(type=openapi.TYPE_STRING, description="图片标签列表"),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户id"),
                "group_order": openapi.Schema(type=openapi.TYPE_STRING, description="分组排序"),
                "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
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
                            items=openapi.Schema(
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
        user_id = data.get("user_id")
        group_name = data.get("group_name")
        group_order = data.get("group_order")
        group_desc = data.get("group_desc")
        pic_url = data.get("pic_url")
        pic_tags = data.get("pic_tags")
        pic_name = data.get("pic_name")
        pic_id = get_distributed_id(worker_id=self.worker_id)

        if not user_id or not group_name or not group_order or not pic_url or not pic_name:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_duplicate_group = (
            f"SELECT group_id FROM {settings.DEFAULT_DB}.ap_agent_pictures WHERE group_name = "
            f"'{group_name}' AND user_id = '{user_id}' LIMIT 1"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_duplicate_group)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    duplicate_data = MysqlOper.get_query_result(cursor)
                    group_id = duplicate_data[0].get('group_id')
                else:
                    group_id = get_distributed_id(worker_id=self.worker_id)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        if pic_tags:
            pic_tags_joined = ','.join(pic_tags)  # 转换为字符串
        else:
            pic_tags_joined = ''
        # 生成 SQL 语句
        sql_insert_pic = (
            f"INSERT INTO {settings.DEFAULT_DB}.ap_agent_pictures "
            f"(user_id, group_name, group_order, group_id,group_desc,  pic_id, pic_name, pic_url, pic_tags) "
            f"VALUES ('{user_id}', '{group_name}', '{group_order}', '{group_id}', '{group_desc}', '{pic_id}', "
            f"'{pic_name}', '{pic_url}', '{pic_tags_joined}')"
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert_pic)
                rowcount = cursor.rowcount

                if rowcount == 1:
                    code = RET.OK
                    message = Language.get(code)
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
        operation_id="201",
        tags=["智能体"],
        operation_summary="获取图片库指定组图片列表",
        operation_description="获取图片库指定组图片列表",
        manual_parameters=[
            openapi.Parameter(
                "group_id",
                openapi.IN_QUERY,
                description="组ID",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "group_order",
                openapi.IN_QUERY,
                description="组当前排序",
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
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户ID"
                                    ),
                                    "group_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组名称"
                                    ),
                                    "group_order": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组id"
                                    ),
                                    "group_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组描述"
                                    ),
                                    "pic_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片ID"
                                    ),
                                    "pic_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片名称"
                                    ),
                                    "pic_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片地址"
                                    ),
                                    "pic_tags": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片标签列表"
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
        data = request.GET
        page_index = data.get("page_index", 1)
        page_count = data.get("page_count", 10)
        user_id = data.get('user_id')
        group_id = data.get('group_id', '')
        group_order = data.get('group_order', 1)

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        if not group_id:
            group_order = 1

        sql_get_pictures = (
            f"SELECT group_name,group_order, group_id, group_desc, pic_id, pic_name, pic_url, pic_tags FROM "
            f"ap_agent_pictures WHERE user_id = '{user_id}' "
            f" AND is_delete = 0 AND group_id = {group_id} AND group_order = '{group_order}' "
        )

        sql_get_pictures_total = (
            f"SELECT count(1) AS total FROM ap_agent_pictures  WHERE user_id = '{user_id}' AND is_delete = 0 AND "
            f" group_id = {group_id} AND group_order = '{group_order}' "
        )
        if page_count is not None:
            sql_get_pictures += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_pictures += " OFFSET " + str(row_index)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_pictures_total)
                total = MysqlOper.get_query_result(cursor)[0].get('total')

            with connection.cursor() as cursor:
                cursor.execute(sql_get_pictures)
                db_data = MysqlOper.get_query_result(cursor)

                ret_data = []

                for each in db_data:
                    each_dict = {
                        'user_id': user_id,
                        'group_name': each.get('group_name'),
                        'group_order': each.get('group_order'),
                        'group_id': each.get('group_id'),
                        'group_desc': each.get('group_desc'),
                        'pic_id': each.get('pic_id'),
                        'pic_name': each.get('pic_name'),
                        'pic_url': each.get('pic_url'),
                        'pic_tags': each.get('pic_tags').split(','),
                    }
                    ret_data.append(each_dict)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, total=total, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="202",
        tags=["智能体"],
        operation_summary="删除分组或者图片",
        operation_description="根据group_id或者pic_id 删除分组或者图",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "pic_id": openapi.Schema(type=openapi.TYPE_STRING, description="pic_id"),
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
        group_id = request.data.get("group_id", '')
        pic_id = request.data.get("pic_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(pic_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.ap_agent_pictures SET is_delete = 1 WHERE group_id = {group_id} "
                f"AND user_id = {user_id}"
            )

        if pic_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.ap_agent_pictures SET is_delete = 1 WHERE pic_id = {pic_id} "
                f"AND user_id = {user_id}"
            )
        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_delete)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="203",
        tags=["智能体"],
        operation_summary="修改分组名称或者图片标签",
        operation_description="根据group_id或者pic_id 修改分组名称或者图片标签",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "pic_id": openapi.Schema(type=openapi.TYPE_STRING, description="pic_id"),
                "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="新的组名称，如果当前传的是group_id"),
                "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="新的组描述，如果当前传的是group_id"),
                "pic_tags": openapi.Schema(type=openapi.TYPE_STRING, description="新的全量标签列表， 如果当前传的是pic_id"),
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
    def put(self, request):
        user_id = request.data.get("user_id")
        group_id = request.data.get("group_id", '')
        pic_id = request.data.get("pic_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(pic_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            group_name = request.data.get('group_name')
            group_desc = request.data.get('group_desc')
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.ap_agent_pictures SET group_name = '{group_name}', "
                f" group_desc = '{group_desc}' WHERE group_id = '{group_id}' "
                f"AND user_id = {user_id}"
            )

        if pic_id:
            pic_tags = request.data.get("pic_tags")
            pic_tags_joined = ','.join(pic_tags)
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.ap_agent_pictures SET pic_tags = '{pic_tags_joined}' WHERE pic_id = '{pic_id}' "
                f"AND user_id = {user_id}"
            )

        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_update)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class AgentDocuments(APIView):
    worker_id = 8889

    @swagger_auto_schema(
        operation_id="204",
        tags=["智能体"],
        operation_summary="智能体文档管理",
        operation_description="智能体文档管理",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "group_name", "file_url", "file_type", "file_name", "group_order"],
            properties={
                "group_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组名称"
                ),
                "file_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文档名称"
                ),
                "file_url": openapi.Schema(type=openapi.TYPE_STRING, description="文档地址"),
                "file_type": openapi.Schema(type=openapi.TYPE_STRING, description="文档类型"),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户id"),
                "group_order": openapi.Schema(type=openapi.TYPE_STRING, description="分组排序"),
                "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
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
                            items=openapi.Schema(
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
        user_id = data.get("user_id")
        group_name = data.get("group_name")
        group_desc = data.get("group_desc")
        group_order = data.get("group_order")
        file_url = data.get("file_url")
        file_name = data.get("file_name")
        file_type = data.get("file_type")
        file_id = get_distributed_id(worker_id=self.worker_id)

        if not user_id or not group_name or not file_url or not file_name or not file_type:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_duplicate_group = (
            f"SELECT group_id FROM {settings.DEFAULT_DB}.ad_agent_documents WHERE group_name = "
            f"'{group_name}' AND user_id = '{user_id}' LIMIT 1"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_duplicate_group)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    duplicate_data = MysqlOper.get_query_result(cursor)
                    group_id = duplicate_data[0].get('group_id')
                else:
                    group_id = get_distributed_id(worker_id=self.worker_id)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        # 生成 SQL 语句
        sql_insert_pic = (
            f"INSERT INTO {settings.DEFAULT_DB}.ad_agent_documents "
            f"(user_id, group_name, group_order,group_desc,  group_id, file_id, file_type, file_name, file_url) "
            f"VALUES ('{user_id}', '{group_name}', '{group_order}','{group_desc}', '{group_id}', '{file_id}', "
            f"'{file_type}', '{file_name}', '{file_url}')"
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert_pic)
                rowcount = cursor.rowcount

                if rowcount == 1:
                    code = RET.OK
                    message = Language.get(code)
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
        operation_id="205",
        tags=["智能体"],
        operation_summary="获取文档库指定组文档列表",
        operation_description="获取文档库指定组文档列表",
        manual_parameters=[
            openapi.Parameter(
                "group_id",
                openapi.IN_QUERY,
                description="组ID",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "group_order",
                openapi.IN_QUERY,
                description="组当前排序",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="当前用id",
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
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户ID"
                                    ),
                                    "group_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组名称"
                                    ),
                                    "group_order": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组id"
                                    ),
                                    "group_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组描述"
                                    ),
                                    "file_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档ID"
                                    ),
                                    "file_type": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档名称"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档地址"
                                    ),
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档地址"
                                    ),
                                    "times_used": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="使用次数"
                                    ),
                                    "file_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档描述"
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
        data = request.GET
        page_index = data.get("page_index", 1)
        page_count = data.get("page_count", 10)
        user_id = data.get('user_id')
        group_id = data.get('group_id', '')
        group_order = data.get('group_order', 1)
        file_url = data.get('file_url')
        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        if not group_id:
            group_order = 1

        sql_get_pictures = (
            f"SELECT group_name,group_order, group_desc, group_id, file_id, file_type, file_name, file_url, "
            f" times_used, file_desc FROM ad_agent_documents WHERE user_id = '{user_id}' "
            f" AND is_delete = 0 AND group_id = '{group_id}' AND group_order = '{group_order}' "
        )

        sql_get_pictures_total = (
            f"SELECT count(1) AS total FROM ad_agent_documents  WHERE user_id = '{user_id}' AND is_delete = 0 AND "
            f" group_id = '{group_id}' AND group_order = '{group_order}' "
        )

        if file_url:
            sql_get_pictures += f" AND file_url LIKE %{file_url}% "
            sql_get_pictures_total += f" AND file_url LIKE %{file_url}% "
        if page_count is not None:
            sql_get_pictures += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_pictures += " OFFSET " + str(row_index)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_pictures_total)
                total = MysqlOper.get_query_result(cursor)[0].get('total')

            with connection.cursor() as cursor:
                cursor.execute(sql_get_pictures)
                db_data = MysqlOper.get_query_result(cursor)

                ret_data = []

                for each in db_data:
                    each_dict = {
                        'user_id': user_id,
                        'group_name': each.get('group_name'),
                        'group_order': each.get('group_order'),
                        'group_desc': each.get('group_desc'),
                        'group_id': each.get('group_id'),
                        'file_id': each.get('file_id'),
                        'file_type': each.get('file_type'),
                        'file_name': each.get('file_name'),
                        'file_url': each.get('file_url'),
                        'times_used': each.get('times_used'),
                        'file_desc': each.get('file_desc'),
                    }
                    ret_data.append(each_dict)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, total=total, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="206",
        tags=["智能体"],
        operation_summary="删除分组或者文档",
        operation_description="根据group_id或者file_id 删除分组或者文档",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "file_id": openapi.Schema(type=openapi.TYPE_STRING, description="pic_id"),
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
        group_id = request.data.get("group_id", '')
        file_id = request.data.get("file_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(file_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.ad_agent_documents SET is_delete = 1 WHERE group_id = {group_id} "
                f"AND user_id = {user_id}"
            )

        if file_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.ad_agent_documents SET is_delete = 1 WHERE file_id = {file_id} "
                f"AND user_id = {user_id}"
            )
        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_delete)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="207",
        tags=["智能体"],
        operation_summary="修改分组名称或者文档描述",
        operation_description="根据group_id或者pic_id 修改分组名称或者文档描述",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "file_id": openapi.Schema(type=openapi.TYPE_STRING, description="file_id"),
                "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="新的组名称，如果当前传的是group_id"),
                "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="新的组描述，如果当前传的是group_id"),
                "file_desc": openapi.Schema(type=openapi.TYPE_STRING, description="文档描述， 如果当前传的是file_id"),
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
    def put(self, request):
        user_id = request.data.get("user_id")
        group_id = request.data.get("group_id", '')
        file_id = request.data.get("file_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(file_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            group_name = request.data.get('group_name')
            group_desc = request.data.get('group_desc')
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.ad_agent_documents SET group_name = '{group_name}', grpup_desc = {group_desc} "
                f" WHERE group_id = '{group_id}' "
                f"AND user_id = {user_id}"
            )

        if file_id:
            file_desc = request.data.get("file_desc")
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.ad_agent_documents SET file_desc = '{file_desc}' WHERE file_id = '{file_id}' "
                f"AND user_id = {user_id}"
            )

        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_update)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class AgentUrls(APIView):
    worker_id = 8822

    @swagger_auto_schema(
        operation_id="208",
        tags=["智能体"],
        operation_summary="智能体url管理",
        operation_description="智能体url管理",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "group_name", "url_name", "group_order"],
            properties={
                "group_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组名称"
                ),
                "url_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="url 名称"
                ),
                # "url_title": openapi.Schema(type=openapi.TYPE_STRING, description="url 标题"),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户id"),
                "group_order": openapi.Schema(type=openapi.TYPE_STRING, description="分组排序"),
                "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
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
                            items=openapi.Schema(
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
        user_id = data.get("user_id")
        group_name = data.get("group_name")
        group_order = data.get("group_order")
        group_desc = data.get("group_desc", '')
        # url_title = data.get("url_title")
        url_name = data.get("url_name")
        url_type = 'url'
        url_id = get_distributed_id(worker_id=self.worker_id)

        if not user_id or not group_name or not url_name or not group_order:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_duplicate_group = (
            f"SELECT group_id FROM {settings.DEFAULT_DB}.au_agent_urls WHERE group_name = "
            f"'{group_name}' AND user_id = '{user_id}' LIMIT 1"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_duplicate_group)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    duplicate_data = MysqlOper.get_query_result(cursor)
                    group_id = duplicate_data[0].get('group_id')
                else:
                    group_id = get_distributed_id(worker_id=self.worker_id)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        # 生成 SQL 语句
        sql_insert_pic = (
            f"INSERT INTO {settings.DEFAULT_DB}.au_agent_urls "
            f"(user_id, group_name, group_order, group_id,group_desc, url_id, url_type, url_name) "
            f"VALUES ('{user_id}', '{group_name}', '{group_order}', '{group_id}', '{group_desc}',  '{url_id}', "
            f"'{url_type}', '{url_name}')"
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert_pic)
                rowcount = cursor.rowcount

                if rowcount == 1:
                    code = RET.OK
                    message = Language.get(code)
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
        operation_id="209",
        tags=["智能体"],
        operation_summary="获取url库指定组url列表",
        operation_description="获取url库指定组url列表",
        manual_parameters=[
            openapi.Parameter(
                "group_id",
                openapi.IN_QUERY,
                description="组ID",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "group_order",
                openapi.IN_QUERY,
                description="组当前排序",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="当前用id",
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
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户ID"
                                    ),
                                    "group_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组名称"
                                    ),
                                    "group_order": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组id"
                                    ),
                                    "group_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="组描述"
                                    ),
                                    "url_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档ID"
                                    ),
                                    "url_type": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档名称"
                                    ),
                                    "url_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档地址"
                                    ),
                                    "url_title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档地址"
                                    ),
                                    "times_used": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="使用次数"
                                    )
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
        data = request.GET
        page_index = data.get("page_index", 1)
        page_count = data.get("page_count", 10)
        user_id = data.get('user_id')
        group_id = data.get('group_id', '')
        group_order = data.get('group_order', 1)
        url_name = data.get('url_name')

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        if not group_id:
            group_order = 1

        sql_get_urls = (
            f"SELECT group_name,group_order, group_id, group_desc, url_id, url_type, url_title, url_name, "
            f" times_used FROM au_agent_urls WHERE user_id = '{user_id}' "
            f" AND is_delete = 0 AND group_id = '{group_id}' AND group_order = '{group_order}' "
        )

        sql_get_urls_total = (
            f"SELECT count(1) AS total FROM au_agent_urls  WHERE user_id = '{user_id}' AND is_delete = 0 AND "
            f" group_id = '{group_id}' AND group_order = '{group_order}' "
        )

        if url_name:
            sql_get_urls += f" AND url_name LIKE %{url_name}% "
            sql_get_urls_total += f" AND url_name LIKE %{url_name}% "

        if page_count is not None:
            sql_get_urls += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_urls += " OFFSET " + str(row_index)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_urls_total)
                total = MysqlOper.get_query_result(cursor)[0].get('total')

            with connection.cursor() as cursor:
                cursor.execute(sql_get_urls)
                db_data = MysqlOper.get_query_result(cursor)

                ret_data = []

                for each in db_data:
                    each_dict = {
                        'user_id': user_id,
                        'group_name': each.get('group_name'),
                        'group_order': each.get('group_order'),
                        'group_id': each.get('group_id'),
                        'group_desc': each.get('group_desc'),
                        'url_id': each.get('url_id'),
                        'url_type': each.get('url_type'),
                        'url_title': each.get('url_title'),
                        'url_name': each.get('url_name'),
                        'times_used': each.get('times_used'),
                    }
                    ret_data.append(each_dict)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, total=total, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="240",
        tags=["智能体"],
        operation_summary="删除分组或者url",
        operation_description="根据group_id或者url_id 删除分组或者url",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "url_id": openapi.Schema(type=openapi.TYPE_STRING, description="pic_id"),
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
        group_id = request.data.get("group_id", '')
        url_id = request.data.get("url_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(url_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.au_agent_urls SET is_delete = 1 WHERE group_id = {group_id} "
                f"AND user_id = {user_id}"
            )

        if url_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.au_agent_urls SET is_delete = 1 WHERE url_id = {url_id} "
                f"AND user_id = {user_id}"
            )
        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_delete)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="211",
        tags=["智能体"],
        operation_summary="修改分组名称或者url标题",
        operation_description="根据group_id或者pic_id 修改分组名称或者url标题",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "url_id": openapi.Schema(type=openapi.TYPE_STRING, description="ur_id"),
                "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="新的组名称，如果当前传的是group_id"),
                "url_title": openapi.Schema(type=openapi.TYPE_STRING, description="url标题， 如果当前传的是url_id"),
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
    def put(self, request):
        user_id = request.data.get("user_id")
        group_id = request.data.get("group_id", '')
        url_id = request.data.get("url_id", '')

        # at least one is valid
        one_valid = bool(group_id) or bool(url_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            group_name = request.data.get('group_name')
            group_desc = request.data.get('group_desc')
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.au_agent_urls SET group_name = '{group_name}', "
                f" group_desc = '{group_desc}' WHERE group_id = '{group_id}' "
                f"AND user_id = {user_id}"
            )

        if url_id:
            url_title = request.data.get("url_title")
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.au_agent_urls SET url_title = '{url_title}' WHERE url_id = '{url_id}' "
                f"AND user_id = {user_id}"
            )

        try:

            with connection.cursor() as cursor:
                cursor.execute(sql_update)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class AgentModels(APIView):
    worker_id = 8890

    @swagger_auto_schema(
        operation_id="213",
        tags=["智能体"],
        operation_summary="智能体模型管理",
        operation_description="创建或者更新智能体模型",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "group_name", "group_order", "agent_type", "avatar_url", "agent_name", "agent_desc",
                      "agent_character", "file_ids"],
            properties={
                "is_edit": openapi.Schema(type=openapi.TYPE_STRING, description="当前行为是否是编辑 0|1"),
                "agent_id": openapi.Schema(type=openapi.TYPE_STRING, description="如果是编辑，则提供agent_id"),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户id"),
                "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="分组名称"),
                "group_order": openapi.Schema(type=openapi.TYPE_INTEGER, description="分组排序"),
                "agent_type": openapi.Schema(type=openapi.TYPE_STRING, description="智能体分类"),
                "avatar_url": openapi.Schema(type=openapi.TYPE_STRING, description="头像URL"),
                "agent_name": openapi.Schema(type=openapi.TYPE_STRING, description="智能体名称"),
                "agent_desc": openapi.Schema(type=openapi.TYPE_STRING, description="智能体描述"),
                "agent_character": openapi.Schema(type=openapi.TYPE_STRING, description="智能体性格"),
                "file_ids": openapi.Schema(type=openapi.TYPE_STRING, description="文件ID列表"),
                "info_agent": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "type_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="类型ID"),
                            "title": openapi.Schema(type=openapi.TYPE_STRING, description="标题"),
                            "placeholder": openapi.Schema(type=openapi.TYPE_STRING, description="占位符"),
                            "info_options": openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "value": openapi.Schema(type=openapi.TYPE_STRING, description="选项值")
                                    }
                                ),
                                description="信息选项"
                            ),
                            "is_required": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="是否必填"),
                            "weight": openapi.Schema(type=openapi.TYPE_INTEGER, description="权重"),
                        }
                    ),
                    description="智能体信息"
                ),
                "agent_prompt": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="智能体提示",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,  # 或者任何适合的类型
                        properties={
                            # 在这里定义数组中对象的属性
                            "agent_prompt": openapi.Schema(type=openapi.TYPE_STRING, description="提示文本")
                        }
                    )
                ),
                "sample_question": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="智能体示例提问",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,  # 或者任何适合的类型
                        properties={
                            # 在这里定义数组中对象的属性
                            "sample_question": openapi.Schema(type=openapi.TYPE_STRING, description="示例问题内容")
                        }
                    )
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
    @transaction.atomic()
    def post(self, request):
        data = request.data
        is_edit = data.get('is_edit', 0)
        user_id = data.get("user_id")
        group_name = data.get("group_name")
        group_order = data.get("group_order")
        group_desc = data.get("group_desc")
        agent_type = data.get("agent_type")
        avatar_url = data.get("avatar_url")
        agent_name = data.get("agent_name")
        agent_desc = data.get("agent_desc")
        agent_character = data.get("agent_character")
        file_ids = data.get("file_ids")
        file_ids = [str(each) for each in file_ids]
        file_ids = ','.join(file_ids)
        agent_prompt = data.get("agent_prompt", [])
        sample_question = data.get("sample_question", [])
        info_agent = data.get('info_agent', [])

        if not int(is_edit):
            agent_id = get_distributed_id(worker_id=self.worker_id)
        else:
            agent_id = data.get("agent_id")

        if not user_id or not group_name or not agent_type or not avatar_url or not agent_name or not agent_desc \
                or not agent_character or not file_ids:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        # 创建和更新共用一个接口
        if is_edit:
            # 删除mysql关联数据
            sql_update = (
                f"UPDATE {settings.DEFAULT_DB}.am_agent_models SET is_delete = 1 WHERE agent_id = '{agent_id}'"
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_update)
                    rowcount = cursor.rowcount
                    if rowcount < 0:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        raise CstException(code=code, message=message)
            except Exception:
                print(traceback.format_exc())
                code = RET.DB_ERR
                message = Language.get(code)
                raise CstException(code=code, message=message)

            # 删除向量数据库数据
            try:
                exist = settings.APP.db.get(where={'user_id': user_id, 'agent_id': agent_id})
                if bool(exist.get('ids')):
                    for each_file in exist.get('metadatas'):
                        try:
                            deleting_file_id = each_file.get('file_id')
                            settings.APP.db.delete(
                                where={'user_id': user_id, 'agent_id': agent_id, 'file_id': deleting_file_id})
                        except Exception:
                            continue
            except Exception:
                print(traceback.format_exc())
                code = RET.DB_ERR
                message = Language.get(code)
                raise CstException(code=code, message=message)
        sql_duplicate_type = (
            f"SELECT group_id FROM {settings.DEFAULT_DB}.am_agent_models WHERE group_name = "
            f"'{group_name}' AND user_id = '{user_id}'  AND is_delete = 0 LIMIT 1"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_duplicate_type)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    duplicate_data = MysqlOper.get_query_result(cursor)
                    group_id = duplicate_data[0].get('group_id')
                else:
                    group_id = get_distributed_id(worker_id=self.worker_id)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)
        # 创建回滚点
        save_id = transaction.savepoint()

        sql_duplicate_group = (
            f"SELECT agent_type_id FROM {settings.DEFAULT_DB}.am_agent_models WHERE group_name = "
            f"'{group_name}' AND user_id = '{user_id}'  AND is_delete = 0 LIMIT 1"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_duplicate_group)
                rowcount_type = cursor.rowcount

                if rowcount_type > 0:
                    duplicate_data_type = MysqlOper.get_query_result(cursor)
                    agent_type_id = duplicate_data_type[0].get('agent_type_id')
                else:
                    agent_type_id = get_distributed_id(worker_id=self.worker_id)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_get_knowledge_base = (
            f"""
                    SELECT 'ad_agent_documents' AS table_name, "document" AS type,file_id AS id,  file_url AS url
                        FROM ad_agent_documents
                        WHERE file_id IN ({file_ids})  AND is_delete = 0

                        UNION

                        SELECT 'au_agent_urls' AS table_name,"url" AS type, url_id AS id, url_name AS url
                        FROM au_agent_urls
                        WHERE url_id IN ({file_ids})  AND is_delete = 0

                        UNION

                        SELECT 'ap_agent_pictures' AS table_name,"picture" AS type, pic_id AS id,  pic_url AS url
                        FROM ap_agent_pictures
                        WHERE pic_id IN ({file_ids})  AND is_delete = 0 ;
                    """
        )

        print(sql_get_knowledge_base)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_knowledge_base)
                db_knowledge_data = MysqlOper.get_query_result(cursor)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        if is_edit:
            agent_id = get_distributed_id(self.worker_id)

        # 插入向量数据库
        url_called_ids = []
        document_called_ids = []
        for each_knowledge_data in db_knowledge_data:
            knowledge_file_url = each_knowledge_data['url']
            knowledge_file_id = each_knowledge_data['id']
            knowledge_file_type = each_knowledge_data['type']

            # TODO  图片暂时不向量化进opensearch, 后期加入
            if knowledge_file_type == 'picture':
                continue
            if knowledge_file_type != 'url':
                knowledge_file_url = settings.OSS_PREFIX + knowledge_file_url

            if knowledge_file_type == 'document':
                document_called_ids.append(knowledge_file_id)
            else:
                url_called_ids.append(knowledge_file_id)
            embedded = settings.APP.db.get(where={'user_id': user_id, 'agent_id': agent_id,
                                                  'file_id': knowledge_file_id, 'file_type': knowledge_file_type})
            if bool(embedded.get('ids')):
                continue

            settings.APP.add(knowledge_file_url, metadata={'user_id': user_id, 'agent_id': agent_id,
                                                           'file_id': knowledge_file_id,
                                                           'file_type': knowledge_file_type})

        # 插入models 库
        sql_insert_model = (
            f"INSERT INTO {settings.DEFAULT_DB}.am_agent_models "
            f"(user_id, agent_id, group_name, group_order, group_id, group_desc, agent_type_name, agent_type_id, "
            f"avatar_url, agent_name, agent_desc, agent_character, file_ids ) "
            f"VALUES ('{user_id}', '{agent_id}', '{group_name}', '{group_order}', '{group_id}', '{group_desc}', "
            f"'{agent_type}', '{agent_type_id}', '{avatar_url}','{agent_name}','{agent_desc}', '{agent_character}', '{file_ids}')"
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert_model)
                rowcount_models = cursor.rowcount
                if rowcount_models > 0:
                    models_success = True
                else:
                    models_success = False
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        # 插入自定义输入框
        agent_add_ids = []
        agent_data = []
        option_success = 0
        agent_success = 0

        if info_agent:

            for each_info_question in info_agent:
                agent_add_id = get_distributed_id(self.worker_id)
                agent_add_ids.append(str(agent_add_id))

                each_info_agent_type_id = each_info_question.get('type_id')
                each_info_agent_title = each_info_question.get('title')
                each_info_agent_placeholder = each_info_question.get('placeholder')
                each_info_agent_info_options = each_info_question.get('info_options')
                each_info_agent_info_is_required = 1 if each_info_question.get('is_required') else 0
                each_info_agent_info_weight = each_info_question.get('weight', 0)
                option_ids = []
                if each_info_agent_info_options:
                    options_data = []
                    for inner_info_question_info_options in each_info_agent_info_options:
                        option_id = get_distributed_id(self.worker_id)
                        option_ids.append(str(option_id))
                        time.sleep(0.05)
                        info_type_id = each_info_agent_type_id
                        option_value = inner_info_question_info_options.get('value')
                        options_data.append((user_id, agent_id, option_id, info_type_id, option_value))
                    try:
                        options_sql = f"""
                        INSERT INTO {settings.ADMIN_DB}.oio_info_options_user (user_id,question_id, option_id, info_type_id,option_value)
                        VALUES %s;
                        """ % ', '.join(['(%s, %s, %s, %s, %s)' for _ in options_data])
                        with connections[settings.ADMIN_DB].cursor() as cursor:
                            cursor.execute(options_sql, [item for sublist in options_data for item in sublist])
                            rowcount_options = cursor.rowcount
                            if rowcount_options == len(options_data):
                                option_success += 1
                            else:
                                transaction.savepoint_rollback(save_id)
                                code = RET.DB_ERR
                                message = Language.get(code)
                                return CstResponse(code=code, message=message)
                    except Exception:
                        print(traceback.format_exc())
                        transaction.savepoint_rollback(save_id)
                        code = RET.DB_ERR
                        message = Language.get(code)
                        raise CstException(code=code, message=message)

                agent_data.append((user_id, agent_add_id, each_info_agent_type_id, agent_id, ','.join(option_ids),
                                   each_info_agent_title, each_info_agent_placeholder, each_info_agent_info_is_required,
                                   each_info_agent_info_weight))

            if agent_data:
                try:
                    # 构建OqQuestionInfoUser的SQL插入语句
                    agents_sql = f"""
                    INSERT INTO {settings.ADMIN_DB}.oq_question_info_user (user_id, question_add_id, info_type_id, question_id, option_ids, title, placeholder, is_required, weight)
                    VALUES %s;
                    """ % ', '.join(['(%s, %s, %s, %s, %s, %s, %s, %s, %s)' for _ in agent_data])
                    with connections[settings.ADMIN_DB].cursor() as cursor:
                        cursor.execute(agents_sql, [item for sublist in agent_data for item in sublist])
                        rowcount_agents = cursor.rowcount

                        if rowcount_agents > 0:
                            agent_success += rowcount_agents
                        else:
                            print(traceback.format_exc())
                            transaction.savepoint_rollback(save_id)
                            code = RET.DB_ERR
                            message = Language.get(code)
                            return CstResponse(code=code, message=message)
                except Exception:
                    print(traceback.format_exc())
                    transaction.savepoint_rollback(save_id)
                    code = RET.DB_ERR
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
            else:
                agent_success = True
        else:
            agent_success = True
        prompt_data = []

        for each_prompt in agent_prompt:
            type = 'prompt'
            prompt_id = get_distributed_id(self.worker_id)
            time.sleep(0.05)
            prompt_data.append((agent_id, type, each_prompt, prompt_id, prompt_id))
        if prompt_data:
            try:
                prompt_sql = f"""
                           INSERT INTO {settings.DEFAULT_DB}.ac_agent_config (agent_id, type, agent_prompt, 
                           prompt_id, sample_id ) VALUES %s;
                           """ % ', '.join(['(%s, %s, %s, %s, %s)' for _ in prompt_data])

                with connection.cursor() as cursor:
                    cursor.execute(prompt_sql, [item for sublist in prompt_data for item in sublist])
                    rowcount_prompt = cursor.rowcount

                    if rowcount_prompt > 0:
                        prompt_success = True
                    else:
                        transaction.savepoint_rollback(save_id)
                        code = RET.DB_ERR
                        message = Language.get(code)
                        return CstResponse(code=code, message=message)
            except Exception:
                print(traceback.format_exc())
                transaction.savepoint_rollback(save_id)
                code = RET.DB_ERR
                message = Language.get(code)
                return CstResponse(code=code, message=message)
        else:
            prompt_success = True

        sample_questio_data = []
        for each_sample in sample_question:
            type = 'question'
            sample_question = each_sample.get('sample_question')
            sample_id = get_distributed_id(self.worker_id)
            time.sleep(0.05)
            sample_questio_data.append((agent_id, type, sample_question, sample_id, sample_id))

        if sample_questio_data:
            try:
                sample_sql = f"""
                           INSERT INTO {settings.DEFAULT_DB}.ac_agent_config (agent_id, type, sample_question, 
                           sample_id, prompt_id ) VALUES %s; """ % ', '.join(['(%s, %s, %s, %s,  %s)' for _ in
                                                                              sample_questio_data])
                with connection.cursor() as cursor:

                    cursor.execute(sample_sql, [item for sublist in sample_questio_data for item in sublist])
                    rowcount_prompt = cursor.rowcount
                    if rowcount_prompt > 0:
                        sample_success = True
                    else:
                        transaction.savepoint_rollback(save_id)
                        code = RET.DB_ERR
                        message = Language.get(code)
                        return CstResponse(code=code, message=message)
            except Exception:
                print(traceback.format_exc())
                transaction.savepoint_rollback(save_id)
                code = RET.DB_ERR
                message = Language.get(code)
                raise CstException(code=code, message=message)
        else:
            sample_success = True

        if models_success and prompt_success and sample_success and option_success == len(agent_data) \
                and agent_success == len(agent_data):

            if document_called_ids:
                placeholders_documents = ', '.join(['%s'] * len(document_called_ids))
                sql_update_call_document_count = (
                    f"UPDATE {settings.DEFAULT_DB}.ad_agent_documents SET times_used = times_used + 1 WHERE "
                    f" file_id IN ({placeholders_documents}) AND is_delete = 0"
                )
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(sql_update_call_document_count, document_called_ids)
                except Exception:
                    print(traceback.format_exc())
                    transaction.savepoint_rollback(save_id)
                    code = RET.DB_ERR
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
            if url_called_ids:
                placeholders_urls = ', '.join(['%s'] * len(url_called_ids))
                sql_update_call_url_count = (
                    f"UPDATE {settings.DEFAULT_DB}.au_agent_urls SET times_used = times_used + 1 WHERE "
                    f" url_id IN ({placeholders_urls}) AND is_delete = 0"
                )
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(sql_update_call_url_count, url_called_ids)
                except Exception:
                    print(traceback.format_exc())
                    transaction.savepoint_rollback(save_id)
                    code = RET.DB_ERR
                    message = Language.get(code)
                    raise CstException(code=code, message=message)

            code = RET.OK
            data = {
                'agent_id': agent_id,
                'group_id': group_id,
                'group_order': group_order
            }
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=data)
        else:
            code = RET.DB_ERR
            message = Language.get(code)
            transaction.savepoint_rollback(save_id)
            return CstResponse(code=code, message=message)

    @swagger_auto_schema(
        operation_id="214",
        tags=["智能体"],
        operation_summary="获取智能体详情列表或者根据智能体ID查询指定智能体详情",
        operation_description="获取url库指定组url列表",
        manual_parameters=[
            openapi.Parameter(
                "group_id",
                openapi.IN_QUERY,
                description="组ID",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "group_order",
                openapi.IN_QUERY,
                description="组当前排序",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="当前用id",
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
                            type=openapi.TYPE_OBJECT,
                            description='智能体详情数据',
                            properties={
                                "agent_type_name": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="按智能体类型分类的数据",
                                    additional_properties=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "agent_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体ID"
                                            ),
                                            "group_name": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="组名称"
                                            ),
                                            "group_order": openapi.Schema(
                                                type=openapi.TYPE_INTEGER, description="组序号"
                                            ),
                                            "group_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="组ID"
                                            ),
                                            "agent_type_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体类型ID"
                                            ),
                                            "avatar_url": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体头像URL"
                                            ),
                                            "agent_name": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体名称"
                                            ),
                                            "agent_desc": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体描述"
                                            ),
                                            "agent_character": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体特征"
                                            ),
                                            "file_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="文件ID"
                                            ),
                                            "config_type": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="配置类型"
                                            ),
                                            "sample_question": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="样例问题"
                                            ),
                                            "agent_prompt": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="智能体提示"
                                            ),
                                            "sample_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="样本ID"
                                            ),
                                            "prompt_id": openapi.Schema(
                                                type=openapi.TYPE_STRING, description="提示ID"
                                            ),
                                            "options": openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                description="智能体配置选项",
                                                items=openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        "info_type_id": openapi.Schema(
                                                            type=openapi.TYPE_INTEGER, description="信息类型ID"
                                                        ),
                                                        "info_type_name": openapi.Schema(
                                                            type=openapi.TYPE_STRING, description="信息类型名称"
                                                        ),
                                                        "title": openapi.Schema(
                                                            type=openapi.TYPE_STRING, description="选项标题"
                                                        ),
                                                        "placeholder": openapi.Schema(
                                                            type=openapi.TYPE_STRING, description="占位符文本"
                                                        ),
                                                        "weight": openapi.Schema(
                                                            type=openapi.TYPE_INTEGER, description="权重"
                                                        ),
                                                        "is_required": openapi.Schema(
                                                            type=openapi.TYPE_BOOLEAN, description="是否必填"
                                                        ),
                                                        "options": openapi.Schema(
                                                            type=openapi.TYPE_ARRAY,
                                                            description="具体选项列表",
                                                            items=openapi.Schema(
                                                                type=openapi.TYPE_OBJECT,
                                                                properties={
                                                                    "option_id": openapi.Schema(
                                                                        type=openapi.TYPE_INTEGER, description="选项ID"
                                                                    ),
                                                                    "value": openapi.Schema(
                                                                        type=openapi.TYPE_STRING, description="选项值"
                                                                    ),
                                                                }
                                                            )
                                                        )
                                                    }
                                                )
                                            ),
                                        }
                                    ),
                                ),
                            },
                        )
                    },
                )
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
        data = request.GET

        user_id = data.get('user_id')
        agent_id = data.get('agent_id', 0)
        group_id = data.get('group_id', '')
        group_order = data.get('group_order', 1)

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        if not group_id:
            group_order = 1

        sql_get_options = f"""
            SELECT
                    oq.question_id,
                    oq.option_ids,
                    GROUP_CONCAT(IFNULL(oio.option_value, '')) AS option_values,
                    oq.info_type_id,
                    oit.info_type_name,
                    oq.title,
                    oq.placeholder,
                    oq.weight,
                    oq.is_required
                FROM
                    {settings.ADMIN_DB}.oq_question_info_user AS oq
                JOIN
                    {settings.ADMIN_DB}.oi_info_types AS oit ON oq.info_type_id = oit.info_type_id
                JOIN
                    {settings.ADMIN_DB}.oio_info_options_user AS oio ON FIND_IN_SET(oio.option_id, oq.option_ids)
                WHERE
                    oq.user_id = {user_id}
                    AND oq.is_delete = 0
                    AND oit.is_delete = 0
                    AND (oio.is_delete = 0 OR oio.is_delete IS NULL)
                GROUP BY
                    oq.question_id,
                    oq.question_add_id,
                    oq.option_ids,
                    oq.info_type_id,
                    oit.info_type_name,
                    oq.title,
                    oq.placeholder,
                    oq.weight,
                    oq.is_required,
                    oq.created_at
                ORDER BY
                    oq.weight, oq.created_at

        """

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_options)
                query_data = MysqlOper.get_query_result(cursor)

                options_data = defaultdict(lambda: defaultdict(list))

                for each_data in query_data:
                    question_id = each_data.get("question_id")
                    option_ids = each_data.get("option_ids")
                    option_values = each_data.get("option_values")
                    info_type_id = each_data.get("info_type_id")
                    info_type_name = each_data.get("info_type_name")
                    title = each_data.get("title")
                    placeholder = each_data.get("placeholder")
                    weight = each_data.get("weight")
                    is_required = each_data.get("is_required")

                    option_ids_list = option_ids.split(",")
                    option_values_list = option_values.split(",")

                    if len(option_ids_list) == len(option_values_list):
                        dictionary_list = [
                            {"option_id": int(a), "value": b}
                            for a, b in zip(option_ids_list, option_values_list)
                        ]
                    else:
                        dictionary_list = []

                    each_dict = {}
                    each_dict['options'] = dictionary_list
                    each_dict['info_type_id'] = info_type_id
                    each_dict['info_type_name'] = info_type_name
                    each_dict['title'] = title
                    each_dict['placeholder'] = placeholder
                    each_dict['weight'] = weight
                    each_dict['is_required'] = is_required
                    options_data[question_id]['options'].append(each_dict)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)
        sql_get_config = (
            f"SELECT am.agent_id, am.group_name,am.group_order, am.group_id, am.agent_type_name, am.agent_type_id, "
            f"am.avatar_url, "
            f"am.agent_name, am.agent_desc, am.agent_character, am.file_ids, ac.type, ac.sample_question, "
            f"ac.agent_prompt, ac.sample_id, ac.prompt_id "
            f"FROM {settings.DEFAULT_DB}.am_agent_models  AS am "
            f"LEFT JOIN  {settings.DEFAULT_DB}.ac_agent_config AS ac ON am.agent_id = ac.agent_id "
            f"WHERE am.user_id = '{user_id}' "
            f" AND am.is_delete = 0 AND am.group_id = '{group_id}' AND am.group_order = '{group_order}' "
        )

        if agent_id:
            sql_get_config += f" AND ac.agent_id = {agent_id} AND am.agent_id = {agent_id}"
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_config)
                db_data = MysqlOper.get_query_result(cursor)

                # agents = defaultdict(dict)
                agents = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
                for each in db_data:
                    agent_id = each.get('agent_id')

                    group_name = each.get('group_name')
                    group_order = each.get('group_order')
                    group_id = each.get('group_id')
                    agent_type_name = each.get('agent_type_name')
                    agent_type_id = each.get('agent_type_id')
                    avatar_url = each.get('avatar_url')
                    agent_name = each.get('agent_name')
                    agent_desc = each.get('agent_desc')
                    agent_character = each.get('agent_character')
                    file_id = each.get('file_ids')
                    config_type = each.get('type')
                    sample_question = each.get('sample_question')
                    agent_prompt = each.get('agent_prompt')
                    sample_id = each.get('sample_id')
                    prompt_id = each.get('prompt_id')
                    agents[agent_type_name][agent_id]['agent_id'] = agent_id
                    agents[agent_type_name][agent_id]['group_name'] = group_name
                    agents[agent_type_name][agent_id]['group_order'] = group_order
                    agents[agent_type_name][agent_id]['group_id'] = group_id
                    agents[agent_type_name][agent_id]['agent_type_name'] = agent_type_name
                    agents[agent_type_name][agent_id]['agent_type_id'] = agent_type_id
                    agents[agent_type_name][agent_id]['avatar_url'] = avatar_url
                    agents[agent_type_name][agent_id]['agent_name'] = agent_name
                    agents[agent_type_name][agent_id]['agent_desc'] = agent_desc
                    agents[agent_type_name][agent_id]['agent_character'] = agent_character
                    agents[agent_type_name][agent_id]['file_id'] = file_id
                    agents[agent_type_name][agent_id]['config_type'] = config_type
                    agents[agent_type_name][agent_id]['sample_question'] = sample_question
                    agents[agent_type_name][agent_id]['agent_prompt'] = agent_prompt
                    agents[agent_type_name][agent_id]['sample_id'] = sample_id
                    agents[agent_type_name][agent_id]['prompt_id'] = prompt_id

                    if agent_id in options_data.keys():
                        agents[agent_type_name][agent_id]['options'] = options_data.get(agent_id)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=agents)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="210",
        tags=["智能体"],
        operation_summary="删除分组或者url",
        operation_description="根据group_id或者url_id 删除分组或者url",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组id"),
                "url_id": openapi.Schema(type=openapi.TYPE_STRING, description="pic_id"),
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
        agent_id = request.data.get('agent_id')
        group_id = request.data.get("group_id")
        # at least one is valid
        one_valid = bool(group_id) or bool(agent_id)
        if not one_valid:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if group_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.am_agent_models SET is_delete = 1 WHERE group_id = {group_id} "
                f"AND user_id = {user_id}"
            )

        if agent_id:
            sql_delete = (
                f"UPDATE {settings.DEFAULT_DB}.am_agent_models SET is_delete = 1 WHERE agent_id = {agent_id} "
                f"AND user_id = {user_id}"
            )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_delete)
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class Groups(APIView):

    @swagger_auto_schema(
        operation_id="220",
        tags=["智能体"],
        operation_summary="获取用户创建的分组信息",
        operation_description="根据user_id筛选分组详情",
        manual_parameters=[
            openapi.Parameter("user_id", openapi.IN_QUERY, description="用户ID", type=openapi.TYPE_STRING)
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="响应码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="响应消息"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "pictures": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description="图片信息数组",
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="组名"),
                                            "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
                                            "group_order": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                          description="组内顺序"),
                                            "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组ID"),
                                            "pic_id": openapi.Schema(type=openapi.TYPE_STRING, description="图片ID"),
                                            "pic_name": openapi.Schema(type=openapi.TYPE_STRING, description="图片名称"),
                                            "pic_tags": openapi.Schema(type=openapi.TYPE_ARRAY,
                                                                       items=openapi.Schema(type=openapi.TYPE_STRING),
                                                                       description="图片标签"),
                                            "pic_url": openapi.Schema(type=openapi.TYPE_STRING, description="图片URL"),
                                        }
                                    )
                                ),
                                "documents": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description="文档信息数组",
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="组名"),
                                            "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
                                            "group_order": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                          description="组内顺序"),
                                            "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组ID"),
                                            "file_id": openapi.Schema(type=openapi.TYPE_STRING, description="文件ID"),
                                            "file_type": openapi.Schema(type=openapi.TYPE_STRING, description="文件类型"),
                                            "file_name": openapi.Schema(type=openapi.TYPE_STRING, description="文件名称"),
                                            "file_url": openapi.Schema(type=openapi.TYPE_STRING, description="文件URL"),
                                            "time_used": openapi.Schema(type=openapi.TYPE_INTEGER, description="使用次数"),
                                            "file_desc": openapi.Schema(type=openapi.TYPE_STRING, description="文件描述"),
                                        }
                                    )
                                ),
                                "urls": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description="链接信息数组",
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="组名"),
                                            "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述"),
                                            "group_order": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                          description="组内顺序"),
                                            "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组ID"),
                                            "url_id": openapi.Schema(type=openapi.TYPE_STRING, description="链接ID"),
                                            "url_type": openapi.Schema(type=openapi.TYPE_STRING, description="链接类型"),
                                            "url_title": openapi.Schema(type=openapi.TYPE_STRING, description="链接标题"),
                                            "url_name": openapi.Schema(type=openapi.TYPE_STRING, description="链接名称"),
                                            "time_used": openapi.Schema(type=openapi.TYPE_INTEGER, description="使用次数"),
                                        }
                                    )
                                ),
                            }
                        )
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
        },
    )
    def get(self, request):
        data = request.GET

        user_id = data.get('user_id')

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_get_pic_groups = (f"""
            SELECT group_name, group_desc, group_order, group_id,pic_id, pic_name, pic_tags, pic_url
            FROM ap_agent_pictures
            WHERE is_delete = 0 AND user_id = {user_id}
            ORDER BY group_name, group_order""")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_pic_groups)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        group_pic_tree = defaultdict(list)
        for group_name, group_desc, group_order, group_id, pic_id, pic_name, pic_tags, pic_url in cursor.fetchall():
            dict_group_pic = {
                'group_name': group_name,
                'group_desc': group_desc,
                'group_order': group_order,
                'group_id': group_id,
                'pic_id': pic_id,
                'pic_name': pic_name,
                'pic_tags': pic_tags,
                'pic_url': pic_url
            }
            group_pic_tree[group_name].append(dict_group_pic)

        sql_get_url_groups = (f"""
                    SELECT group_name,group_desc, group_order, group_id,url_id, url_type, url_title, url_name, times_used
                    FROM au_agent_urls
                    WHERE is_delete = 0 AND user_id = {user_id}
                    ORDER BY group_name, group_order""")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_url_groups)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        group_url_tree = defaultdict(list)
        for group_name, group_desc, group_order, group_id, url_id, url_type, url_title, url_name, time_used in cursor.fetchall():
            dict_group_url = {
                'group_name': group_name,
                'group_desc': group_desc,
                'group_order': group_order,
                'group_id': group_id,
                'url_id': url_id,
                'url_type': url_type,
                'url_title': url_title,
                'url_name': url_name,
                'time_used': time_used,
            }
            group_url_tree[group_name].append(dict_group_url)

        sql_get_document_groups = (f"""
                    SELECT group_name,group_desc, group_order, group_id,file_id, file_type, file_name, file_url, times_used, file_desc
                    FROM ad_agent_documents
                    WHERE is_delete = 0 AND user_id = {user_id}
                    ORDER BY group_name, group_order""")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_document_groups)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        group_docuement_tree = defaultdict(list)
        for group_name, group_desc, group_order, group_id, file_id, file_type, file_name, file_url, time_used, file_desc in cursor.fetchall():
            dict_group_document = {
                'group_name': group_name,
                'group_desc': group_desc,
                'group_order': group_order,
                'group_id': group_id,
                'file_id': file_id,
                'file_type': file_type,
                'file_name': file_name,
                'file_url': file_url,
                'time_used': time_used,
                'file_desc': file_desc,
            }
            group_docuement_tree[group_name].append(dict_group_document)

        ret_data = {
            "pictures": group_pic_tree,
            "documents": group_docuement_tree,
            "urls": group_url_tree,
        }
        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=ret_data)


class AgenClassificationGroup(APIView):

    @swagger_auto_schema(
        operation_id="221",
        tags=["智能体"],
        operation_summary="获取用户创建的模型的分组和类型信息",
        operation_description="根据user_id筛选智能体模型的分组和类型信息",
        manual_parameters=[
            openapi.Parameter("user_id", openapi.IN_QUERY, description="用户ID", type=openapi.TYPE_STRING)
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="响应码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="响应消息"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "group_tree": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="按分组信息组织的智能体模型",
                                    additionalProperties=openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "group_name": openapi.Schema(type=openapi.TYPE_STRING,
                                                                             description="分组名称"),
                                                "group_id": openapi.Schema(type=openapi.TYPE_STRING,
                                                                           description="分组ID"),
                                            }
                                        )
                                    )
                                ),
                                "type_tree": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="按类型信息组织的智能体模型",
                                    additionalProperties=openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "agent_type_name": openapi.Schema(type=openapi.TYPE_STRING,
                                                                                  description="智能体类型名称"),
                                                "agent_type_id": openapi.Schema(type=openapi.TYPE_STRING,
                                                                                description="智能体类型ID"),
                                            }
                                        )
                                    )
                                ),
                            }
                        )
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
        },
    )
    def get(self, request):

        worker_id = 9008
        user_id = request.GET.get('user_id')
        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_query = f"""
            SELECT 
            group_name, group_id,group_order, agent_type_name, agent_type_id
            FROM am_agent_models
            WHERE is_delete = 0 AND user_id = {user_id}
            ORDER BY group_name, group_order, agent_type_name
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                query_results = cursor.fetchall()

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        group_tree = defaultdict(list)
        type_tree = defaultdict(list)

        if query_results:
            for row in query_results:
                group_dict = {
                    'group_name': row[0],
                    'group_id': row[1],
                    'group_order': row[2]
                }
                type_dict = {
                    'agent_type_name': row[3],
                    'agent_type_id': row[4]
                }
                group_tree[row[0]].append(group_dict)
                type_tree[row[3]].append(type_dict)

        else:
            default_group_id = get_distributed_id(worker_id=worker_id)
            group_dict = {
                'group_name': "默认分组",
                'group_id': default_group_id,
                'group_order': 1
            }

            group_tree["默认分组"].append(group_dict)
        type_dict_work = {
            'agent_type_name': "工作",
            'agent_type_id': 505498631458439
        }
        type_dict_life = {
            'agent_type_name': "学习",
            'agent_type_id': 505498631458440
        }
        type_tree["工作"].append(type_dict_work)
        type_tree["学习"].append(type_dict_life)
        ret_data = {
            "group_tree": group_tree,
            "type_tree": type_tree,
        }
        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=ret_data)


class AgentGroups(APIView):

    @swagger_auto_schema(
        operation_id="241",
        tags=["智能体"],
        operation_summary="获取用户下的智能体分组信息",
        operation_description="根据user_id获取用户下的智能体分组信息",
        manual_parameters=[
            openapi.Parameter("user_id", openapi.IN_QUERY, description="用户ID", type=openapi.TYPE_STRING)
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="响应码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="响应消息"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "agent": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description="图片信息数组",
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "group_name": openapi.Schema(type=openapi.TYPE_STRING, description="组名"),
                                            "group_order": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                          description="组内顺序"),
                                            "group_id": openapi.Schema(type=openapi.TYPE_STRING, description="组ID"),
                                            "group_desc": openapi.Schema(type=openapi.TYPE_STRING, description="分组描述")
                                        }
                                    )
                                )
                            }
                        )
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="无效的请求参数",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="内部服务器错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_INTEGER, description="错误码"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="错误信息")
                    },
                ),
            ),
        },
    )
    def get(self, request):
        data = request.GET

        user_id = data.get('user_id')

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_get_agent_groups = (f"""
            SELECT group_name, group_order, group_id, group_desc FROM am_agent_models WHERE is_delete = 0 AND user_id = {user_id}
            ORDER BY group_name, group_order""")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_agent_groups)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        group_agent_tree = defaultdict(list)
        for group_name, group_order, group_id, group_desc in cursor.fetchall():
            dict_group_pic = {
                'group_name': group_name,
                'group_order': group_order,
                'group_id': group_id,
                'group_desc': group_desc
            }
            group_agent_tree[group_name].append(dict_group_pic)

        ret_data = {
            "agent": group_agent_tree,
        }
        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=ret_data)


class AgentChat(APIView):

    @swagger_auto_schema(
        operation_id="230",
        tags=["智能体"],
        operation_summary="智能体对话",
        operation_description="智能体对话获取上下文，传递给对话接口",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["agent_id", "options"],
            properties={
                "agent_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="智能体ID"
                ),
                "options": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "option_title": openapi.Schema(type=openapi.TYPE_STRING, description="选项标题"),
                            "option_value": openapi.Schema(type=openapi.TYPE_STRING, description="选项值")
                        }
                    ),
                    description="选项列表"
                )
            }

        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="响应代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="响应消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "content": openapi.Schema(type=openapi.TYPE_STRING, description="匹配到的上下文内容"),

                            }
                        )
                    }
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

        agent_id = data.get('agent_id')
        options = data.get('options', [])

        options_data = []
        for each in options:
            option_title = each.get('option_title')
            option_value = each.get('option_value')
            pair_question = option_title + ':' + option_value
            options_data.append(pair_question)
        question = '; '.join(options_data)
        sql_get_model_base = (
            f"SELECT am.agent_name, am.agent_desc, am.agent_character, ac.agent_prompt, am.file_ids FROM "
            f"{settings.DEFAULT_DB}.am_agent_models as am LEFT JOIN {settings.DEFAULT_DB}.ac_agent_config as ac "
            f" ON am.agent_id = ac.agent_id WHERE am.agent_id = {agent_id} AND ac.type = 'prompt' "
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_model_base)
                db_data = MysqlOper.get_query_result(cursor)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if db_data:
            agent_name = db_data[0]['agent_name']
            agent_desc = db_data[0]['agent_desc']
            agent_character = db_data[0]['agent_character']
            agent_prompt = db_data[0]['agent_prompt']
            file_ids = db_data[0].get('file_ids')

        else:
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_get_pics = (
            f"SELECT pic_url, pic_tags FROM {settings.DEFAULT_DB}.ap_agent_pictures WHERE pic_id "
            f"in ({file_ids}) AND is_delete = 0"
        )
        pictures = []
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_pics)
                pic_data = MysqlOper.get_query_result(cursor)

                for each_pic in pic_data:
                    pic_url = each_pic['pic_url']
                    pic_tags = each_pic['pic_tags']
                    pictures.append(
                        {
                            "pic_url": settings.OSS_PREFIX + pic_url,
                            "pic_tags": pic_tags
                        }
                    )
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        try:
            embeded_db_content = settings.APP.query(question, citations=True, where={'agent_id': agent_id})

            if not embeded_db_content:
                prompts = ''
            else:
                prompts = generate_structured_prompt_agent(question, agent_name, agent_desc, agent_character,
                                                     agent_prompt, pictures,
                                                     embeded_db_content[0][0] if embeded_db_content else '')
            # redis存储，方便对话接口去拿
            r = get_redis_connection("prompts")
            prompts_to_redis_name = "agent"
            prompts_to_redis_key = agent_id
            prompts_to_redis_value = json.dumps({"prompts": prompts}, ensure_ascii=False)
            r.hset(prompts_to_redis_name, prompts_to_redis_key, prompts_to_redis_value)

            content = {
                "question": question,
                "context": embeded_db_content[0][0] if embeded_db_content else '',
                "agent_id": agent_id
            }
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=content)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)


class AgentGroupEdit(APIView):

    @swagger_auto_schema(
        operation_id="233",
        tags=["智能体"],
        operation_summary="修改智能体分组",
        operation_description="修改智能体分组",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "group_id", "group_name"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID"
                ),
                "group_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组ID"
                ),
                "group_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组名称"
                ),
                "group_desc": openapi.Schema(
                    type=openapi.TYPE_STRING, description="分组描述"
                )
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="响应代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="响应消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "content": openapi.Schema(type=openapi.TYPE_STRING, description="匹配到的上下文内容"),

                            }
                        )
                    }
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
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        group_name = data.get('group_name')
        group_desc = data.get('group_desc')
        if not user_id or not group_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        sql_edit = f" UPDATE {settings.DEFAULT_DB}.am_agent_models SET group_name = '{group_name}', group_desc" \
                   f" = '{group_desc}' WHERE  group_id = '{group_id}' AND is_delete = 0 AND user_id = '{user_id}'"

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_edit)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            logger.error(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)
