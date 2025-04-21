import ast
import json
import logging
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from django.db import connection, connections
from django.http import QueryDict
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from rest_framework import status
from rest_framework.views import APIView

from language.language_pack import RET, Language
from utils.cst_class import CstException, CstResponse
from utils.distributed_id_generator.get_id import get_distributed_id
from utils.gadgets import gadgets
from utils.mq_utils import RabbitMqUtil
from utils.prompts import generate_structured_prompt, generate_structured_prompt_tutor
from utils.sql_oper import MysqlOper

logger = logging.getLogger("view")


class UQDUserQuestionDetailsView(APIView):
    @swagger_auto_schema(
        operation_id="103",
        tags=["v3.5"],
        operation_summary="用户创建模型或问题集",
        operation_description="此端点允许用户创建模型或问题集。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="行业ID"
                ),
                "module_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="模块ID"
                ),
                "occu_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="职业ID"
                ),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="子职业ID"
                ),
                "info_questions": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="信息问题",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "type_id": openapi.Schema(
                                type=openapi.TYPE_INTEGER, description="类型ID"
                            ),
                            "title": openapi.Schema(
                                type=openapi.TYPE_STRING, description="标题"
                            ),
                            "placeholder": openapi.Schema(
                                type=openapi.TYPE_STRING, description="占位符"
                            ),
                            "info_options": openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                description="信息选项",
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "value": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="选项值"
                                        ),
                                    },
                                ),
                            ),
                            "is_required": openapi.Schema(
                                type=openapi.TYPE_BOOLEAN, description="是否必填"
                            ),
                            "weight": openapi.Schema(
                                type=openapi.TYPE_INTEGER, description="权重"
                            ),
                        },
                    ),
                ),
                "emp_duration_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="雇佣期限ID"
                ),
                "expertise_level_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="专业水平ID"
                ),
                "character_avatar": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色头像"
                ),
                "character_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色名称"
                ),
                "character_greetings": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色问候语"
                ),
                "is_public": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN, description="是否公开"
                ),
                "hint": openapi.Schema(type=openapi.TYPE_STRING, description="提示"),
                "character_desc": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色描述"
                ),
                "character_achievements": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色成就"
                ),
                "assistant_title": openapi.Schema(
                    type=openapi.TYPE_STRING, description="助手标题"
                ),
                "assistant_content": openapi.Schema(
                    type=openapi.TYPE_STRING, description="助手内容"
                ),
                "related_document": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="相关文档",
                    properties={
                        "file": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="文件",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件URL"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件名"
                                    ),
                                },
                            ),
                        ),
                        "video": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="视频",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件URL"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件名"
                                    ),
                                },
                            ),
                        ),
                        "pics": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="图片",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件URL"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件名"
                                    ),
                                },
                            ),
                        ),
                        "url": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="URL",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "file_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件URL"
                                    ),
                                    "file_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文件名"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                "refuse_reason": openapi.Schema(
                    type=openapi.TYPE_STRING, description="拒绝原因"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "question_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="问题ID"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        user_build_model_api = (
                settings.ADMIN_PUBLIC_API_DOMAIN + settings.ADMIN_USER_BUILD_MODEL
        )

        response = requests.post(url=user_build_model_api, json=request.data)
        if response.status_code == 200:
            api_data = json.loads(response.text)

            auto_reviewed = True
            if api_data.get("code") == 2000:
                model_created = True
                question_id = api_data.get("data").get("question_id")

                # 逻辑更改， 私有模型不需要审核
                is_public = request.data.get("is_public")

                if not int(is_public):
                    mutable_data = dict(request.data)
                    mutable_data["question_id"] = question_id
                    mutable_data["status"] = 3
                    q_data = QueryDict("", mutable=True)
                    q_data.update(mutable_data)

                    response_auto_review = requests.put(
                        url=user_build_model_api, json=mutable_data
                    )
                    if response_auto_review.status_code == 200:
                        auto_review_data = json.loads(
                            response_auto_review.text)

                        if auto_review_data.get("code") == 2000:
                            auto_reviewed = True
                        else:
                            auto_reviewed = False
                    else:
                        auto_reviewed = False
            else:
                model_created = False

            if all([auto_reviewed, model_created]):

                code = RET.OK
                message = Language.get(code)
                ret_data = {"question_id": question_id}
                mq_data = {
                    "exchange": "digital_assist_exchange",
                    "queue": "digital_assist_query",
                    "routing_key": "DigitalAssistant",
                    "type": "direct",
                    "msg": {
                        "clerk_code": question_id,
                        "company_code": question_id,
                        "knowledge_code": question_id,
                    },
                }

                rabbit_mq = RabbitMqUtil()

                rabbit_mq.send_handle(mq_data)

                return CstResponse(code=code, message=message, data=ret_data)
            else:
                code = RET.DB_ERR
                message = Language.get(code)
                raise CstException(code=code, message=message)
        else:
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="105",
        tags=["v3.5"],
        operation_summary="编辑用户创建的问题集",
        operation_description="此端点允许编辑用户创建的问题集。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "question_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="问题ID"
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="行业ID"
                ),
                "module_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="模块ID"
                ),
                "occu_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="职业ID"
                ),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="子职业ID"
                ),
                "emp_duration_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="雇佣期限ID"
                ),
                "expertise_level_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="专业水平ID"
                ),
                "character_avatar": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色头像"
                ),
                "character_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色名称"
                ),
                "character_greetings": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色问候语"
                ),
                "is_public": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN, description="是否公开"
                ),
                "hint": openapi.Schema(type=openapi.TYPE_STRING, description="提示"),
                "character_desc": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色描述"
                ),
                "character_achievements": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色成就"
                ),
                "assistant_title": openapi.Schema(
                    type=openapi.TYPE_STRING, description="助手标题"
                ),
                "assistant_content": openapi.Schema(
                    type=openapi.TYPE_STRING, description="助手内容"
                ),
                "related_document": openapi.Schema(
                    type=openapi.TYPE_STRING, description="相关文档"
                ),
                "refuse_reason": openapi.Schema(
                    type=openapi.TYPE_STRING, description="拒绝原因"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "question_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="问题ID"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Not Found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def put(self, request):
        data = request.data

        user_build_model_api = (
                settings.ADMIN_PUBLIC_API_DOMAIN + settings.ADMIN_USER_BUILD_MODEL
        )

        response = requests.put(user_build_model_api, json=data)

        if response.status_code == 200:
            api_data = json.loads(response.text)

            if api_data.get("code") == 2000:
                question_id = api_data.get("data").get("question_id")
                code = RET.OK
                message = Language.get(code)
                ret_data = {"question_id": question_id}
                return CstResponse(code=code, message=message, data=ret_data)
        else:
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="104",
        tags=["v3.5"],
        operation_summary="删除用户自建的问题集或模型",
        operation_description="此端点允许删除用户自建的问题集或模型。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "question_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="问题ID"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "question_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="问题ID"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Not Found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    def delete(self, request):
        data = request.data

        user_build_model_api = (
                settings.ADMIN_PUBLIC_API_DOMAIN + settings.ADMIN_USER_BUILD_MODEL
        )

        response = requests.delete(url=user_build_model_api, json=data)

        if response.status_code == 200:
            api_data = json.loads(response.text)

            if api_data.get("code") == 2000:
                question_id = api_data.get("data").get("question_id")
                code = RET.OK
                message = Language.get(code)
                ret_data = {"question_id": question_id}
                return CstResponse(code=code, message=message, data=ret_data)
        else:
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="106",
        tags=["v3.5"],
        operation_summary="获取用户自建问题列表",
        operation_description="此端点允许用户获取他们自建问题列表。",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="用户ID",
            ),
            openapi.Parameter(
                name="page_index",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="页面索引",
            ),
            openapi.Parameter(
                name="page_count",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="页面数量",
            ),
            openapi.Parameter(
                name="is_public",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                description="是否公开",
            ),
            openapi.Parameter(
                name="industry_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="行业ID",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户ID."
                                    ),
                                    "question_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="问题ID."
                                    ),
                                    "character_avatar": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色头像."
                                    ),
                                    "character_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色名称."
                                    ),
                                    "character_greetings": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色问候语."
                                    ),
                                    "hint": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="提示."
                                    ),
                                    "character_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色描述."
                                    ),
                                    "character_achievements": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色成就."
                                    ),
                                    "assistant_title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="助手标题."
                                    ),
                                    "assistant_content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="助手内容."
                                    ),
                                    "refuse_reason": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="拒绝原因."
                                    ),
                                    "is_public": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN, description="是否公开."
                                    ),
                                    "status": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="状态."
                                    ),
                                },
                            ),
                            description="问题详细信息列表.",
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总计."
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息."
                        ),
                    },
                ),
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Not Found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):

        data = request.GET
        user_id = data.get("user_id")
        page_index = data.get("page_index")
        page_count = data.get("page_count")
        is_public = data.get("is_public")
        industry_id = data.get("industry_id", "")

        industry_map = {
            "1": 1001,  # 角色扮演
            "2": 1000,  # 生活助理
            "3": 1003,  # 人物互动
            "4": 1004,  # 工作助理
            "5": 1005,  # 全部
        }
        sql_get_model_details = f"""
                SELECT user_id, question_id,module_id,example_question,
                    character_avatar, character_name, character_greetings,
                    is_public,assistant_title, assistant_content,
                    refuse_reason, status
                FROM {settings.ADMIN_DB}.uqd_user_question_details
                WHERE user_id={user_id} AND is_delete = 0  AND is_public = {is_public} """

        sql_get_model_details_total = f"""
                        SELECT COUNT(DISTINCT(question_id)) AS total
                        FROM {settings.ADMIN_DB}.uqd_user_question_details
                        WHERE user_id={user_id} AND is_delete = 0 AND is_public = {is_public} """

        if industry_id:
            industry_id = industry_map.get(industry_id)

            if industry_id not in [1004, 1005]:
                sql_get_model_details += f" AND industry_id = {industry_id}"
                sql_get_model_details_total += f" AND industry_id = {industry_id}"
            elif industry_id == 1004:
                sql_get_model_details += f" AND industry_id NOT IN (1001,1000, 1003)"
                sql_get_model_details_total += (
                    f" AND industry_id NOT IN (1001,1000, 1003)"
                )
            else:
                print(4444)

        sql_get_model_details += " ORDER BY created_at"

        if page_count is not None:
            sql_get_model_details += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_model_details += " OFFSET " + str(row_index)

        logger.error(sql_get_model_details)
        logger.error(sql_get_model_details_total)

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_model_details_total)
                query_total_data = MysqlOper.get_query_result(cursor)
                query_total = query_total_data[0].get("total", 0)

            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_model_details)
                query_data = MysqlOper.get_query_result(cursor)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)

        list_query_data = []
        for each_data in query_data:
            each_model_data = {}

            question_id = each_data.get("question_id")
            module_id = each_data.get("module_id")
            character_avatar = each_data.get("character_avatar", "")

            character_name = each_data.get("character_name", "")
            character_greetings = each_data.get("character_greetings", "")
            hint = each_data.get("hint", "")
            character_desc = each_data.get("character_desc", "")
            character_achievements = each_data.get(
                "character_achievements", "")
            assistant_title = each_data.get("assistant_title", "")
            assistant_content = each_data.get("assistant_content", "")
            example_question = each_data.get("example_question", "")
            refuse_reason = each_data.get("refuse_reason", "")
            is_public = each_data.get("is_public", "")
            status = each_data.get("status", "")

            each_model_data["user_id"] = user_id
            each_model_data["question_id"] = question_id
            each_model_data["module_id"] = module_id
            each_model_data["character_avatar"] = character_avatar
            each_model_data["character_name"] = character_name
            each_model_data["character_greetings"] = character_greetings
            each_model_data["hint"] = hint
            each_model_data["example_question"] = example_question
            each_model_data["character_desc"] = character_desc
            each_model_data["character_achievements"] = character_achievements
            each_model_data["assistant_title"] = assistant_title
            each_model_data["assistant_content"] = assistant_content
            each_model_data["refuse_reason"] = refuse_reason
            each_model_data["is_public"] = is_public
            each_model_data["status"] = status
            list_query_data.append(each_model_data)
        code = RET.OK
        message = Language.get(code)
        return CstResponse(
            code=code, message=message, data=list_query_data, total=query_total
        )


class UQDUserQuestionDetailsContent(APIView):
    @swagger_auto_schema(
        operation_id="107",
        tags=["v3.5"],
        operation_summary="获取用户自建问题的详细内容",
        operation_description="此端点允许获取用户自建问题的详细内容。",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                name="question_id",
                in_=openapi.IN_QUERY,
                description="问题ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功获取用户问题详情",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="用户问题详情数据",
                            properties={
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="用户ID"
                                ),
                                "question_id": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="问题ID"
                                ),
                                "industry_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="行业ID"
                                ),
                                "module_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="模块ID"
                                ),
                                "occu_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="职业ID"
                                ),
                                "sub_occu_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="二级职业ID"
                                ),
                                "emp_duration_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="工作时长ID"
                                ),
                                "expertise_level_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="专业程度ID"
                                ),
                                "character_avatar": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="角色头像"
                                ),
                                "character_name": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="角色名称"
                                ),
                                "character_greetings": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="角色问候语"
                                ),
                                "hint": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="提示"
                                ),
                                "character_desc": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="角色描述"
                                ),
                                "character_achievements": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="角色成就"
                                ),
                                "assistant_content": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="助手内容"
                                ),
                                "status": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="状态"
                                ),
                                "files": openapi.Schema(
                                    type=openapi.TYPE_OBJECT, description="文件信息"
                                ),
                                "question_data": openapi.Schema(
                                    type=openapi.TYPE_OBJECT, description="问题数据"
                                ),
                            },
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        data = request.GET
        user_id = data.get("user_id")
        question_id = data.get("question_id")

        sql_get_model_details = f"""
                SELECT user_id, question_id, question_add_ids, industry_id, module_id,
                    occu_id, sec_occu_id, occu_duration_id, expertise_level_id,
                    character_avatar, character_name, character_greetings,
                    is_public, hint, character_desc, character_achievements,
                    assistant_title, assistant_content,
                    refuse_reason, status,example_question 
                FROM {settings.ADMIN_DB}.uqd_user_question_details
                WHERE user_id={user_id} AND question_id = {question_id} AND is_delete = 0 ORDER BY created_at """

        try:

            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_model_details)
                query_data = MysqlOper.get_query_result(cursor)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)

        if query_data:
            list_query_data = []
            for each_data in query_data:
                each_model_data = {}

                question_id = each_data.get("question_id")
                industry_id = each_data.get("industry_id")
                module_id = each_data.get("module_id")
                occu_id = each_data.get("occu_id")
                sec_occu_id = each_data.get("sec_occu_id")
                occu_duration_id = each_data.get("occu_duration_id")
                expertise_level_id = each_data.get("expertise_level_id")
                character_avatar = each_data.get("character_avatar")
                character_name = each_data.get("character_name")
                character_greetings = each_data.get("character_greetings")
                example_question = each_data.get("example_question")
                hint = each_data.get("hint")
                is_public = each_data.get("is_public")
                character_desc = each_data.get("character_desc")
                character_achievements = each_data.get(
                    "character_achievements")
                assistant_content = each_data.get("assistant_content")
                assistant_title = each_data.get("assistant_title")
                refuse_reason = each_data.get("industry_id")
                status = each_data.get("status")

                # ---------------------start 取出关联上传的文件 ---------------------
                sql_get_related_document = (
                    f"SELECT  file_url,  group_code, file_name FROM {settings.DEFAULT_DB}.ce_enterprise_files "
                    f"WHERE code = {question_id} AND  is_delete = 0 AND create_by = {user_id}"
                    f" AND file_category = 5")

                with connection.cursor() as cursor:
                    cursor.execute(sql_get_related_document)
                    file_data = MysqlOper.get_query_result(cursor)

                    file_dict = defaultdict(list)

                    for each_file in file_data:
                        file_url = each_file.get("file_url")
                        group_code = each_file.get("group_code")
                        file_name = each_file.get("file_name")

                        file_dict[group_code].append(
                            {"file_url": file_url, "file_name": file_name}
                        )

                # ---------------------end 取出关联上传的文件 end---------------------

                # ---------------------start 取出关联问题 start---------------------
                sql_get_related_add_questions = f"""
                            SELECT
                                oq.question_id,
                                oq.question_add_id,
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
                            LEFT JOIN
                                {settings.ADMIN_DB}.oio_info_options_user AS oio ON FIND_IN_SET(oio.option_id, oq.option_ids)
                            WHERE
                                oq.question_id = {question_id}
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
                                oq.weight, oq.created_at;

                        """
                with connections[settings.ADMIN_DB].cursor() as cursor:
                    cursor.execute(sql_get_related_add_questions)
                    question_data = MysqlOper.get_query_result(cursor)

                    list_question_data = []

                    for each_data in question_data:
                        each_data_dict = {}
                        option_ids = each_data.get("option_ids")
                        option_values = each_data.get("option_values")
                        info_type_id = each_data.get("info_type_id")
                        info_type_name = each_data.get("info_type_name")
                        title = each_data.get("title")
                        placeholder = each_data.get("placeholder")
                        weight = each_data.get("weight")
                        is_required = each_data.get("is_required")

                        if option_ids and option_values:
                            option_ids_list = option_ids.split(",")
                            option_values_list = option_values.split(",")

                            if len(option_ids_list) == len(option_values_list):
                                dictionary_list = [
                                    {"option_id": int(a), "value": b}
                                    for a, b in zip(option_ids_list, option_values_list)
                                ]
                            else:
                                dictionary_list = {}
                        else:
                            dictionary_list = {}

                        each_data_dict["info_options"] = dictionary_list
                        each_data_dict["type_id"] = info_type_id
                        each_data_dict["info_type_name"] = info_type_name
                        each_data_dict["title"] = title
                        each_data_dict["placeholder"] = placeholder
                        each_data_dict["weight"] = weight
                        each_data_dict["is_required"] = is_required
                        list_question_data.append(each_data_dict)

                each_model_data["user_id"] = user_id
                each_model_data["question_id"] = question_id
                each_model_data["industry_id"] = industry_id
                each_model_data["module_id"] = module_id
                each_model_data["occu_id"] = occu_id
                each_model_data["sub_occu_id"] = sec_occu_id
                each_model_data["emp_duration_id"] = occu_duration_id
                each_model_data["expertise_level_id"] = expertise_level_id
                each_model_data["character_avatar"] = character_avatar
                each_model_data["character_name"] = character_name
                each_model_data["character_greetings"] = character_greetings
                each_model_data["hint"] = hint
                each_model_data["is_public"] = is_public
                each_model_data["character_desc"] = character_desc
                each_model_data["character_achievements"] = character_achievements
                each_model_data["assistant_title"] = assistant_title
                each_model_data["example_question"] = example_question
                each_model_data["assistant_content"] = assistant_content
                each_model_data["status"] = status
                each_model_data["files"] = file_dict
                each_model_data["question_data"] = list_question_data
                list_query_data.append(each_model_data)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(
                code=code,
                message=message,
                data=list_query_data)
        else:
            logger.error(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class RemoteDictView(APIView):
    @swagger_auto_schema(
        operation_id="108",
        tags=["v3.5"],
        operation_summary="获取远程字典",
        operation_description="此端点允许用户并发获取获取远程字典的数据。",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功获取所有数据",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="返回的数据",
                            properties={
                                "industry": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="行业数据",
                                ),
                                "occupation": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="职业数据",
                                ),
                                "sec_occupation": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="二级职业数据",
                                ),
                                "duration": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="工作时长数据",
                                ),
                                "expertise_level": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="专业程度数据",
                                ),
                                "modules": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description="模块数据",
                                ),
                            },
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal Server Error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误编码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        # 初始化请求链接
        url_dict = {
            "industry": settings.ADMIN_PUBLIC_API_DOMAIN +
                        settings.ADMIN_INDUSTRY_DICT,
            "occupation": settings.ADMIN_PUBLIC_API_DOMAIN +
                          settings.ADMIN_OCCUPATION_DICT,
            "sec_occupation": settings.ADMIN_PUBLIC_API_DOMAIN +
                              settings.ADMIN_SEC_OCCUPATION_DICT,
            "duration": settings.ADMIN_PUBLIC_API_DOMAIN +
                        settings.ADMIN_DURATION_DICT,
            "expertise_level": settings.ADMIN_PUBLIC_API_DOMAIN +
                               settings.ADMIN_EXPERTISE_LEVEL_DICT,
            "modules": settings.ADMIN_PUBLIC_API_DOMAIN +
                       settings.ADMIN_MODULE_DICT,
        }

        # 创建一个线程池
        with ThreadPoolExecutor(max_workers=6) as executor:
            # 创建一个session对象
            session = FuturesSession(executor=executor)
            session.mount("http://", HTTPAdapter(max_retries=3))
            session.mount("https://", HTTPAdapter(max_retries=3))

            # 并发发送请求
            futures = {key: session.get(url) for key, url in url_dict.items()}

            # 获取所有响应
            responses = {key: future.result()
                         for key, future in futures.items()}

        ret_data = {}
        # 判断响应状态
        for key, response in responses.items():
            if response.status_code == 200:
                api_data = json.loads(response.text)
                if api_data.get("code") == 2000:
                    # 根据不同的key处理数据
                    if key == "industry":
                        # 处理industry的数据
                        ret_data["industry"] = api_data.get("data")
                    elif key == "occupation":
                        # 处理occupation的数据
                        ret_data["occupation"] = api_data.get("data")
                    elif key == "sec_occupation":
                        # 处理occupation的数据
                        ret_data["sec_occupation"] = api_data.get("data")
                    elif key == "duration":
                        # 处理occupation的数据
                        ret_data["duration"] = api_data.get("data")
                    elif key == "expertise_level":
                        # 处理occupation的数据
                        ret_data["expertise_level"] = api_data.get("data")
                    elif key == "modules":
                        # 处理occupation的数据
                        ret_data["modules"] = api_data.get("data")

                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
            else:
                code = RET.DB_ERR
                message = Language.get(code)
                raise CstException(code=code, message=message)

        return CstResponse(
            code=RET.OK, message=Language.get(
                RET.OK), data=ret_data)


class SvaMeList(APIView):
    worker_id = 100001

    @swagger_auto_schema(
        operation_id="109",
        tags=["V5.5"],
        operation_summary="创建『我』",
        operation_description="This endpoint allows for the creation of a new user profile with various personal "
                              "details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["photo", "name"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户Id"
                ),
                "photo": openapi.Schema(type=openapi.TYPE_STRING, description="我的图片"),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="名字"),
                "age": openapi.Schema(type=openapi.TYPE_INTEGER, description="年龄"),
                "occupation": openapi.Schema(
                    type=openapi.TYPE_STRING, description="职业"
                ),
                "gender": openapi.Schema(type=openapi.TYPE_STRING, description="性别"),
                "education": openapi.Schema(type=openapi.TYPE_STRING, description="学历"),
                "major": openapi.Schema(type=openapi.TYPE_STRING, description="专业"),
                "hobbies": openapi.Schema(type=openapi.TYPE_STRING, description="兴趣爱好"),
                "region": openapi.Schema(type=openapi.TYPE_STRING, description="地区"),
                "greeting": openapi.Schema(type=openapi.TYPE_STRING, description="问候语"),
                "relationship_status": openapi.Schema(
                    type=openapi.TYPE_STRING, description="感情状况"
                ),
                "dream": openapi.Schema(type=openapi.TYPE_STRING, description="梦想"),
                "income": openapi.Schema(type=openapi.TYPE_INTEGER, description="收入"),
                "image_description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="形象描述"
                ),
                "document_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文档地址"
                ),
                "image_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="图片地址"
                ),
                "video_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="视频地址"
                ),
                "extend": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Profile successfully created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Missing required parameters or invalid data",
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
        photo = data.get("photo", "")
        name = data.get("name", "")
        age = data.get("age") or 0
        occupation = data.get("occupation", "")
        gender = data.get("gender") or 3
        education = data.get("education") or 8
        major = data.get("major", "")
        hobbies = data.get("hobbies", "")
        region = data.get("region", "")
        greeting = data.get("greeting", "")
        relationship_status = data.get("relationship_status", "")
        dream = data.get("dream", "")
        income = data.get("income") or 0.00
        image_description = data.get("image_description", "")
        document_url = data.get("document_url", "")
        image_url = data.get("image_url", "")
        video_url = data.get("video_url", "")
        extend = data.get("extend", [])
        me_id = get_distributed_id(worker_id=self.worker_id)

        required_params = ["photo", "name"]

        extend = json.dumps(extend, ensure_ascii=False)

        print(extend)
        print("extend")
        missing_params = [
            param for param in required_params if not data.get(param)]

        if missing_params:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_create_me = f"""
            INSERT INTO {settings.DEFAULT_DB}.sva_me (
                user_id, me_id, photo, name, age, occupation, gender, education,
                major, hobbies, region, greeting, relationship_status, dream, income,
                image_description, document_url, image_url, video_url, extend
            ) VALUES (
                {user_id}, {me_id}, '{photo}', '{name}', {age}, '{occupation}', {gender}, '{education}',
                '{major}', '{hobbies}', '{region}', '{greeting}', '{relationship_status}', '{dream}',
                {income}, '{image_description}', '{document_url}', '{image_url}', '{video_url}', '{extend}'
            )
            """

        print(sql_create_me)
        try:
            with connection.cursor() as cursor:

                cursor.execute(sql_create_me)

                rowcount = cursor.rowcount

                if rowcount > 0:
                    embedded = settings.APP.db.get(where={'user_id': user_id, 'me_id': me_id})

                    print(embedded)
                    print('ddddddddddd')
                    if bool(embedded.get('ids')):
                        user_id = embedded.get('metadatas')[0].get('user_id')
                        settings.APP.db.delete(where={'user_id': user_id, 'me_id': me_id})
                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                        try:
                            if image_url:
                                settings.APP.add(image_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())

                        try:
                            if document_url:
                                settings.APP.add(video_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                    else:
                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                        try:
                            if image_url:
                                settings.APP.add(image_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())

                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())

                    ret_data = {"me_id": me_id}
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(
                        code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="110",
        tags=["V5.5"],
        operation_summary="获取『我』",
        operation_description="This endpoint retrieves the user profile based on the provided user ID, with optional pagination.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "me_id",
                openapi.IN_QUERY,
                description="主形象ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "page_index",
                openapi.IN_QUERY,
                description="页码",
                type=openapi.TYPE_INTEGER,
                default=1,
            ),
            openapi.Parameter(
                "page_count",
                openapi.IN_QUERY,
                description="每页数量",
                type=openapi.TYPE_INTEGER,
                default=10,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully retrieved user profile",
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
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "hobbies": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="兴趣爱好"
                                    ),
                                    "region": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="地区"
                                    ),
                                    "greeting": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问候语"
                                    ),
                                    "relationship_status": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="感情状况"
                                    ),
                                    "income": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="收入"
                                    ),
                                    "image_description": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="形象描述"
                                    ),
                                    "document_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="文档地址"
                                    ),
                                    "image_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片地址"
                                    ),
                                    "video_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="视频地址"
                                    ),
                                    "me_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="档案ID"
                                    ),
                                    "photo": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户照片"
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="名字"
                                    ),
                                    "age": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="年龄"
                                    ),
                                    "occupation": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="职业"
                                    ),
                                    "gender": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="性别"
                                    ),
                                    "education": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="学历"
                                    ),
                                    "major": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业"
                                    ),
                                    "extend": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                                    ),
                                },
                                description="用户档案详情",
                            ),
                            description="用户档案数据列表",
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总共用户档案数量"
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
    def get(self, request):
        user_id = request.query_params.get("user_id")
        me_id = request.query_params.get("me_id")
        page_index = request.query_params.get("page_index")
        page_count = request.query_params.get("page_count")

        params = [user_id]
        sql_query = (
            f"SELECT me_id, photo, name,age, occupation, gender, education, major, hobbies,  region, "
            f"  greeting, relationship_status,dream,income, image_description, document_url,"
            f" image_url, video_url, extend  FROM {settings.DEFAULT_DB}.sva_me WHERE user_id = %s AND is_delete = 0")

        if me_id:
            sql_query += " AND me_id = %s "
            params.extend([me_id])

        sql_query += " ORDER BY created_at DESC "

        if page_index is not None:
            if page_count is not None:
                offset = (int(page_index) - 1) * int(page_count)

                sql_query += " LIMIT %s OFFSET %s"
                params.extend([int(page_count), int(offset)])

        sql_total = f"SELECT COUNT(user_id) AS total FROM {settings.DEFAULT_DB}.sva_me WHERE user_id = %s AND is_delete = 0 "

        ret_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_total, [user_id])
                results = MysqlOper.get_query_result(cursor)
                total = results[0].get("total")

            with connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                results = MysqlOper.get_query_result(cursor)
                for each in results:
                    dict_data = {}
                    hobbies = each.get("hobbies")
                    region = each.get("region")
                    greeting = each.get("greeting")
                    relationship_status = each.get("relationship_status")
                    income = each.get("income")
                    image_description = each.get("image_description")
                    document_url = each.get("document_url")
                    image_url = each.get("image_url")
                    video_url = each.get("video_url")
                    me_id = each.get("me_id")
                    photo = each.get("photo")
                    name = each.get("name")
                    age = each.get("age")
                    occupation = each.get("occupation")
                    gender = each.get("gender")
                    education = each.get("education")
                    major = each.get("major")
                    extend = each.get("extend")
                    dream = each.get("dream")
                    dict_data["hobbies"] = hobbies
                    dict_data["region"] = region
                    dict_data["greeting"] = greeting
                    dict_data["relationship_status"] = relationship_status
                    dict_data["income"] = income
                    dict_data["image_description"] = image_description
                    dict_data["document_url"] = document_url
                    dict_data["image_url"] = image_url
                    dict_data["video_url"] = video_url
                    dict_data["me_id"] = me_id
                    dict_data["photo"] = photo
                    dict_data["name"] = name
                    dict_data["age"] = age
                    dict_data["occupation"] = occupation
                    dict_data["gender"] = gender
                    dict_data["education"] = education
                    dict_data["major"] = major
                    dict_data["dream"] = dream
                    dict_data["extend"] = extend
                    ret_data.append(dict_data)

                code = RET.OK
                message = Language.get(code)
                return CstResponse(
                    code=code, message=message, data=ret_data, total=total
                )
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="111",
        tags=["V5.5"],
        operation_summary="删除『我』",
        operation_description="This endpoint allows for the deletion of a user profile using user ID and profile ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "me_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "me_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="档案ID"),
            },
            description="Required user ID and profile ID for deletion",
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Profile successfully deleted",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Missing required parameters or invalid data",
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
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Data not found",
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
    def delete(self, request):
        data = request.data
        user_id = data.get("user_id")
        me_id = data.get("me_id")

        sql_delete = (
            f"UPDATE {settings.DEFAULT_DB}.sva_me a "
            f" JOIN {settings.DEFAULT_DB}.sva_tutor b ON a.me_id = b.me_id "
            f"SET a.is_delete = 1, b.is_delete = 1  WHERE a.user_id = %s AND  a.me_id = %s")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_delete, [user_id, me_id])
                rowcount = cursor.rowcount
                if rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
                else:
                    code = RET.DATA_NOT_FOUND
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="112",
        tags=["V5.5"],
        operation_summary="更新『我』",
        operation_description="This endpoint allows for the updating of an existing user profile.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "me_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "me_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="档案ID"),
                "photo": openapi.Schema(type=openapi.TYPE_STRING, description="我的图片"),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="名字"),
                "age": openapi.Schema(type=openapi.TYPE_INTEGER, description="年龄"),
                "occupation": openapi.Schema(
                    type=openapi.TYPE_STRING, description="职业"
                ),
                "gender": openapi.Schema(type=openapi.TYPE_STRING, description="性别"),
                "education": openapi.Schema(type=openapi.TYPE_STRING, description="学历"),
                "major": openapi.Schema(type=openapi.TYPE_STRING, description="专业"),
                "hobbies": openapi.Schema(type=openapi.TYPE_STRING, description="兴趣爱好"),
                "region": openapi.Schema(type=openapi.TYPE_STRING, description="地区"),
                "greeting": openapi.Schema(type=openapi.TYPE_STRING, description="问候语"),
                "relationship_status": openapi.Schema(
                    type=openapi.TYPE_STRING, description="感情状况"
                ),
                "dream": openapi.Schema(type=openapi.TYPE_STRING, description="梦想"),
                "income": openapi.Schema(type=openapi.TYPE_INTEGER, description="收入"),
                "image_description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="形象描述"
                ),
                "document_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文档地址"
                ),
                "image_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="图片地址"
                ),
                "video_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="视频地址"
                ),
                "extend": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                ),
            },
            description="Required user ID, profile ID and other optional fields for updating",
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Profile successfully updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Missing required parameters, invalid data, or no fields to update",
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
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Data not found",
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
    def put(self, request):
        data = request.data
        user_id = data.get("user_id")
        me_id = data.get("me_id")
        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        # 创建一个字典，只包含有值的参数
        fields_to_update = {
            key: value
            for key, value in data.items()
            if value is not None and key not in ["user_id", "me_id"]
        }

        # 如果没有要更新的字段，返回错误
        if not fields_to_update:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        # 动态构建SQL语句
        set_clause = ", ".join(
            [f"{key} = %s" for key in fields_to_update.keys()])
        sql_update = f"UPDATE {settings.DEFAULT_DB}.sva_me SET {set_clause} WHERE user_id = %s and me_id = %s"

        document_url = data.get("document_url", "")
        image_url = data.get("image_url", "")
        video_url = data.get("video_url", "")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update, list(
                    fields_to_update.values()) + [user_id, me_id])
                print(list(fields_to_update.values()) + [user_id, me_id])
                rowcount = cursor.rowcount
                if rowcount > 0:
                    embedded = settings.APP.db.get(where={'user_id': user_id, 'me_id': me_id})

                    print(embedded)
                    print('ddddddddddd')
                    if bool(embedded.get('ids')):
                        user_id = embedded.get('metadatas')[0].get('user_id')
                        settings.APP.db.delete(where={'user_id': user_id, 'me_id': me_id})
                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                        try:
                            if image_url:
                                settings.APP.add(image_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())

                        try:
                            if document_url:
                                settings.APP.add(video_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                    else:
                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                        try:
                            if image_url:
                                settings.APP.add(image_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())

                        try:
                            if document_url:
                                settings.APP.add(document_url, metadata={'user_id': user_id, 'me_id': me_id})
                        except Exception:
                            print(traceback.format_exc())
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
                else:
                    code = RET.DATA_NOT_FOUND
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class SvaTutorList(APIView):
    worker_id = 100002

    @swagger_auto_schema(
        operation_id="199",
        tags=["V5.5"],
        operation_summary="创建个人导师",
        operation_description="This endpoint allows for the creation of a new tutor profile associated with a user and a character.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "avatar", "character_name", "greeting", "sort"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "avatar": openapi.Schema(
                    type=openapi.TYPE_STRING, description="导师头像URL"
                ),
                "character_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色名称"
                ),
                "greeting": openapi.Schema(type=openapi.TYPE_STRING, description="问候语"),
                "implicit_hint": openapi.Schema(
                    type=openapi.TYPE_STRING, description="隐含提示"
                ),
                "introduction": openapi.Schema(
                    type=openapi.TYPE_STRING, description="导师简介"
                ),
                "influence": openapi.Schema(
                    type=openapi.TYPE_STRING, description="影响力描述"
                ),
                "document": openapi.Schema(
                    type=openapi.TYPE_STRING, description="相关文件URL"
                ),
                "image": openapi.Schema(
                    type=openapi.TYPE_STRING, description="导师图片URL"
                ),
                "website": openapi.Schema(
                    type=openapi.TYPE_STRING, description="个人或相关网站URL"
                ),
                "me_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户档案ID"
                ),
                "sort": openapi.Schema(type=openapi.TYPE_INTEGER, description="位置"),
                "is_copied": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="是否从推荐导师选择的"
                ),
                "extend": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                ),
            },
            description="Required fields for creating a new tutor profile",
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="Tutor profile successfully created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Missing required parameters or invalid data",
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
        avatar = data.get("avatar")
        character_name = data.get("character_name")
        greeting = data.get("greeting")
        implicit_hint = data.get("implicit_hint")
        introduction = data.get("introduction")
        influence = data.get("influence")
        document = data.get("document_url")
        image = data.get("image_url")
        website = data.get("website")
        me_id = data.get("me_id")
        extend = data.get("extend")
        tutor_id = get_distributed_id(self.worker_id)
        unbinded_tutor_id = data.get("unbinded_tutor_id")
        sort = data.get("sort")
        is_copied = data.get("is_copied", 0)
        required_params = [
            "user_id",
            "character_name",
            "greeting",
            "me_id",
            "sort"]

        missing_params = [
            param for param in required_params if not data.get(param)]

        if missing_params:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_check_duplicate = (
            f"SELECT count(character_name) AS character_count FROM {settings.DEFAULT_DB}.sva_tutor WHERE user_id = %s AND me_id = %s AND"
            f" character_name like %s AND is_delete = 0 AND user_id = {user_id}")
        sql_check_duplicate_params = [user_id, me_id, character_name + "%"]

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_check_duplicate, sql_check_duplicate_params)
                duplicate_data = MysqlOper.get_query_result(cursor)
                character_count = duplicate_data[0].get("character_count")
        except Exception:
            code = RET.ERROR_CHANGE_TUTOR
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        # sql_rebind_tutor = f"UPDATE {settings.DEFAULT_DB}.sva_tutor SET status = 1 WHERE tutor_id = {unbinded_tutor_id}"
        # try:
        #     with connection.cursor() as cursor:
        #         cursor.execute(sql_check_duplicate, sql_check_duplicate_params)
        #         if cursor.rowcount > 0:
        #             # 如果导师重复,则重新绑定之前解绑的导师
        #             cursor.execute(sql_rebind_tutor)
        #             if cursor.rowcount > 0:
        #                 code = RET.CHARACTER_DUPLICATE
        #                 message = Language.get(code)
        #                 return CstResponse(code=code, message=message)
        #             else:
        #                 code = RET.ERROR_CHANGE_TUTOR
        #                 message = Language.get(code)
        #                 return CstResponse(code=code, message=message)
        # except Exception:
        #     print(traceback.format_exc())
        #     code = RET.DB_ERR
        #     message = Language.get(code)
        #     raise CstException(code=code, message=message)
        if int(character_count) > 0:
            if "-" in character_name:
                character_name = character_name.split("-")[0] + character_count
            else:
                character_name = character_name + f"-{character_count}"
        sql_create_tutor = f"""
            INSERT INTO {settings.DEFAULT_DB}.sva_tutor (
                user_id, me_id, tutor_id,  avatar, character_name, greeting, implicit_hint,
                introduction, influence, document, image, website, sort, is_copied,  extend
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql_create_tutor,
                    [
                        user_id,
                        me_id,
                        tutor_id,
                        avatar,
                        character_name,
                        greeting,
                        implicit_hint,
                        introduction,
                        influence,
                        document,
                        image,
                        website,
                        sort,
                        is_copied,
                        extend,
                    ],
                )
                if cursor.rowcount > 0:
                    origin_contexts = (
                        f"角色名称是： {character_name}， 问候语是： {greeting}， 隐性提示词是： {implicit_hint}， "
                        f"介绍是：{introduction}， 影响是： {influence}")
                    mq_data = {
                        "exchange": "digital_tutor_exchange",
                        "queue": "digital_tutor_query",
                        "routing_key": "DigitalTutor",
                        "type": "direct",
                        "msg": {
                            "user_id": user_id,
                            "me_id": me_id,
                            "tutor_id": tutor_id,
                            "origin_contexts": origin_contexts,
                            "document_url": document,
                        },
                    }
                    rabbit_mq = RabbitMqUtil()

                    rabbit_mq.send_handle(mq_data)

                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception as e:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(
                code=code,
                message=message +
                        f" Error: {str(e)}")

    @swagger_auto_schema(
        operation_id="120",
        tags=["V5.5"],
        operation_summary="获取导师列表",
        operation_description="This endpoint retrieves tutor profiles based on the provided query parameters.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
            openapi.Parameter(
                "me_id",
                openapi.IN_QUERY,
                description="用户档案ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "page_index",
                openapi.IN_QUERY,
                description="页码",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=1,
            ),
            openapi.Parameter(
                "page_count",
                openapi.IN_QUERY,
                description="每页数量",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=10,
            ),
            openapi.Parameter(
                "tutor_id",
                openapi.IN_QUERY,
                description="导师ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "is_built_in",
                openapi.IN_QUERY,
                description="是否获取内建导师， 1/0， " "此处填写则me_id不填，因为内建导师不存在对应me_id",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully retrieved tutor profiles",
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
                            description="List of tutor profiles",
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户ID"
                                    ),
                                    "me_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户档案ID"
                                    ),
                                    "tutor_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="导师ID"
                                    ),
                                    "avatar": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="导师头像URL"
                                    ),
                                    "character_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="角色名称"
                                    ),
                                    "greeting": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问候语"
                                    ),
                                    "implicit_hint": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="隐含提示"
                                    ),
                                    "introduction": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="导师简介"
                                    ),
                                    "influence": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="影响力描述"
                                    ),
                                    "document": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="相关文件URL"
                                    ),
                                    "image": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="导师图片URL"
                                    ),
                                    "website": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="个人或相关网站URL",
                                    ),
                                    "extend": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                                    ),
                                    "sort": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="位置"
                                    ),
                                    "get_all": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="是否获取所有1/0",
                                    ),
                                    "is_copied": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="是否从推荐导师选择的",
                                    ),
                                    "is_built_in": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="获取示例导师这个字段传1， 否则传0",
                                    ),
                                },
                            ),
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总数"
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
    def get(self, request):
        user_id = request.query_params.get("user_id")
        me_id = request.query_params.get("me_id")
        page_index = request.query_params.get("page_index")
        page_count = request.query_params.get("page_count")
        tutor_id = request.query_params.get("tutor_id")
        is_built_in = request.query_params.get("is_built_in")
        get_all = request.query_params.get("get_all")
        params = []
        params_total = []
        sql_total = f"SELECT COUNT(tutor_id) AS total FROM {settings.DEFAULT_DB}.sva_tutor WHERE is_delete = 0"

        sql_query = f"""
            SELECT user_id,me_id,tutor_id, avatar,character_name,greeting, implicit_hint, introduction,
               influence,document, image, website, sort, status,  is_copied,  extend  FROM {settings.DEFAULT_DB}.sva_tutor
            WHERE  is_delete = 0
            """

        if is_built_in:
            sql_total += " AND is_built_in = %s"
            params_total.extend([is_built_in])

        if user_id is not None:
            sql_total += " AND user_id = %s "
            sql_query += " AND user_id = %s "
            params.extend([user_id])
            params_total.extend([user_id])

        if tutor_id:
            sql_query += " AND tutor_id = %s "
            params.extend([tutor_id])
        if me_id:
            sql_query += " AND me_id = %s "
            sql_total += " AND me_id = %s "
            params.extend([me_id])
            params_total.extend([me_id])

        if is_built_in:
            sql_query += " AND is_built_in = %s "
            params.extend([is_built_in])

        sql_query += " ORDER BY created_at DESC "
        if page_index is not None:
            if page_count is not None:
                offset = (int(page_index) - 1) * int(page_count)
                sql_query += " LIMIT %s OFFSET %s"
                params.extend([int(page_count), int(offset)])

        ret_data = []

        print(sql_query)
        print(params)
        print(request.query_params)
        print("---------")
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_total, params_total)
                results = MysqlOper.get_query_result(cursor)
                total = results[0].get("total")
            with connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                results = MysqlOper.get_query_result(cursor)
                for each in results:
                    dict_data = {}
                    user_id = each.get("user_id")
                    me_id = each.get("me_id")
                    tutor_id = each.get("tutor_id")
                    avatar = each.get("avatar")
                    character_name = each.get("character_name")
                    greeting = each.get("greeting")
                    implicit_hint = each.get("implicit_hint")
                    introduction = each.get("introduction")
                    influence = each.get("influence")
                    document = each.get("document")
                    image = each.get("image")
                    website = each.get("website")
                    is_copied = each.get("is_copied")
                    sort = each.get("sort")
                    status = each.get("status")
                    extend = each.get("extend")
                    dict_data["user_id"] = user_id
                    dict_data["me_id"] = me_id
                    dict_data["tutor_id"] = tutor_id
                    dict_data["avatar"] = avatar
                    dict_data["character_name"] = character_name
                    dict_data["greeting"] = greeting
                    dict_data["implicit_hint"] = implicit_hint
                    dict_data["introduction"] = introduction
                    dict_data["influence"] = influence
                    dict_data["document"] = document
                    dict_data["image"] = image
                    dict_data["website"] = website
                    dict_data["is_copied"] = is_copied
                    dict_data["extend"] = extend
                    dict_data["sort"] = sort
                    dict_data["status"] = status
                    ret_data.append(dict_data)

                code = RET.OK
                message = Language.get(code)
                return CstResponse(
                    code=code, message=message, data=ret_data, total=total
                )
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="114",
        tags=["V5.5"],
        operation_summary="删除导师",
        operation_description="This endpoint deletes a tutor profile based on the provided user ID, me ID, and tutor ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "me_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户档案ID"
                ),
                "tutor_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="导师ID"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully deleted the tutor profile",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Number of rows affected",
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
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Tutor profile not found",
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
    def delete(self, request):
        data = request.data
        user_id = data.get("user_id")
        me_id = data.get("me_id")
        tutor_id = data.get("tutor_id")

        sql_delete = f"""
            UPDATE {settings.DEFAULT_DB}.sva_tutor
            SET is_delete = 1
            WHERE user_id = %s AND me_id = %s AND tutor_id = %s
            """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_delete, [user_id, me_id, tutor_id])
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message, total=1)
                else:
                    code = RET.DATA_NOT_FOUND
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
        except Exception as e:
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="115",
        tags=["V5.5"],
        operation_summary="更新导师",
        operation_description="This endpoint updates a tutor profile based on the provided user ID, me ID, and tutor ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "me_id", "tutor_id", "avatar", "character_name"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "me_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户档案ID"
                ),
                "tutor_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="导师ID"
                ),
                "avatar": openapi.Schema(type=openapi.TYPE_STRING, description="头像"),
                "character_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="角色名称"
                ),
                "greeting": openapi.Schema(type=openapi.TYPE_STRING, description="问候语"),
                "implicit_hint": openapi.Schema(
                    type=openapi.TYPE_STRING, description="隐性提示"
                ),
                "introduction": openapi.Schema(
                    type=openapi.TYPE_STRING, description="介绍"
                ),
                "influence": openapi.Schema(type=openapi.TYPE_STRING, description="影响"),
                "document": openapi.Schema(type=openapi.TYPE_STRING, description="文档"),
                "image": openapi.Schema(type=openapi.TYPE_STRING, description="图片"),
                "status": openapi.Schema(
                    type=openapi.TYPE_STRING, description="当前绑定状态， 默认1， 解绑传 0"
                ),
                "website": openapi.Schema(type=openapi.TYPE_STRING, description="网站"),
                "extend": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="扩展字段，这里传对象，你们传什么格式，后面返回的就是什么格式",
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully updated the tutor profile",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Response code"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Response message"
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
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Tutor profile not found",
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
    def put(self, request):
        data = request.data
        user_id = data.get("user_id")
        me_id = data.get("me_id")
        tutor_id = data.get("tutor_id")
        status = data.get("status")

        if not user_id or not me_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        fields_to_update = {
            key: value
            for key, value in data.items()
            if value is not None and key not in ["user_id", "me_id", "tutor_id"]
        }

        print(2222222222)

        print(fields_to_update)
        if not fields_to_update:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        set_clause = ", ".join(
            [f"{key} = %s" for key in fields_to_update.keys()])
        sql_update = f"""
            UPDATE {settings.DEFAULT_DB}.sva_tutor
            SET {set_clause}
            WHERE user_id = %s AND me_id = %s AND tutor_id = %s
            """

        print(sql_update)
        print(list(fields_to_update.values()))
        print(data)
        print("]]]]]]]]]]]]]]]")
        character_name = data.get("character_name")
        greeting = data.get("greeting")
        implicit_hint = data.get("implicit_hint")
        introduction = data.get("introduction")
        influence = data.get("influence")
        document = data.get("document_url")
        extend = data.get("extend")

        origin_contexts = (
            f"角色名称是： {character_name}， 问候语是： {greeting}， 隐性提示词是： {implicit_hint}， "
            f"介绍是：{introduction}， 影响是： {influence}, 附加内容是：{extend}")
        mq_data = {
            "exchange": "digital_tutor_exchange",
            "queue": "digital_tutor_query",
            "routing_key": "DigitalTutor",
            "type": "direct",
            "msg": {
                "user_id": user_id,
                "me_id": me_id,
                "tutor_id": tutor_id,
                "origin_contexts": origin_contexts,
                "document_url": document,
            },
        }
        rabbit_mq = RabbitMqUtil()

        rabbit_mq.send_handle(mq_data)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update, list(
                    fields_to_update.values()) + [user_id, me_id, tutor_id], )
                print("==========")
                print(sql_update)
                print(list(fields_to_update.values()) +
                      [user_id, me_id, tutor_id])
                if cursor.rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
                else:
                    code = RET.DATA_NOT_FOUND
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class GetRegion(APIView):
    @swagger_auto_schema(
        operation_id="116",
        tags=["V5.5"],
        operation_summary="获取地区",
        operation_description="获取地区",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully updated the tutor profile",
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
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "code": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="邮编"
                                ),
                                "name": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="名称"
                                ),
                            },
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
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Tutor profile not found",
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
        sql_query = f"SELECT code,name FROM {settings.ADMIN_DB}.chatadmin_system_area WHERE level = 1 "

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_query)
                data = MysqlOper.get_query_result(cursor)
                ret_data = [
                    {"code": each.get("code"), "name": each.get("name")}
                    for each in data
                ]
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class BatchGetTutorMe(APIView):
    @swagger_auto_schema(
        operation_id="117",
        tags=["V5.5"],
        operation_summary="获取我&导师信息",
        operation_description="根据ME_ID批量获取导师信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["me_ids"],
            properties={
                "me_ids": openapi.Schema(
                    type=openapi.TYPE_STRING, description="字符串形式数组"
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
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="User ID"
                                    ),
                                    "me_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="ME ID"
                                    ),
                                    "tutor": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="具体查看获取导师接口",
                                    ),
                                    "me": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="具体查看获取我接口",
                                    ),
                                },
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
        me_ids = data.get("me_ids")
        me_ids = ast.literal_eval(me_ids)
        if not me_ids:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_query = """
            SELECT
                user_id,
                me_id,
                photo,
                name,
                age,
                occupation,
                gender,
                education,
                major,
                hobbies,
                region,
                greeting,
                relationship_status,
                dream,
                income,
                image_description,
                document_url,
                image_url,
                video_url,
                extend,
                is_built_in
            FROM
                sva_me
            WHERE
                me_id IN %s AND is_delete = 0 AND is_built_in = 0
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query, [me_ids])
                data = MysqlOper.get_query_result(cursor)

                ret_data = []

                for each in data:
                    dict_each = defaultdict(gadgets.recursive_defaultdict)

                    user_id = each.get("user_id")
                    me_id = each.get("me_id")
                    photo = each.get("photo")
                    name = each.get("name")
                    age = each.get("age")
                    occupation = each.get("occupation")
                    gender = each.get("gender")
                    education = each.get("education")
                    major = each.get("major")
                    hobbies = each.get("hobbies")
                    region = each.get("region")
                    greeting = each.get("greeting")
                    relationship_status = each.get("relationship_status")
                    dream = each.get("dream")
                    income = each.get("income")
                    image_description = each.get("image_description")
                    document_url = each.get("document_url")
                    image_url = each.get("image_url")
                    video_url = each.get("video_url")
                    extend = each.get("extend")
                    is_built_in = each.get("is_built_in")
                    dict_each["me"]["user_id"] = user_id
                    dict_each["me"]["me_id"] = me_id
                    dict_each["me"]["photo"] = photo
                    dict_each["me"]["name"] = name
                    dict_each["me"]["age"] = age
                    dict_each["me"]["occupation"] = occupation
                    dict_each["me"]["gender"] = gender
                    dict_each["me"]["education"] = education
                    dict_each["me"]["major"] = major
                    dict_each["me"]["hobbies"] = hobbies
                    dict_each["me"]["region"] = region
                    dict_each["me"]["greeting"] = greeting
                    dict_each["me"]["relationship_status"] = relationship_status
                    dict_each["me"]["dream"] = dream
                    dict_each["me"]["income"] = income
                    dict_each["me"]["image_description"] = image_description
                    dict_each["me"]["image_url"] = image_url
                    dict_each["me"]["video_url"] = video_url
                    dict_each["me"]["extend"] = extend
                    dict_each["me"]["is_built_in"] = is_built_in
                    dict_each["me"]["document_url"] = document_url
                    sql_query_tutor = f"""
                        SELECT user_id, me_id, tutor_id, avatar, character_name, greeting, implicit_hint, introduction,
                        influence, document, image, website, sort, is_copied, extend, is_built_in,status FROM {settings.DEFAULT_DB}.sva_tutor
                        WHERE is_delete = 0 AND is_built_in = 0 AND me_id = {me_id} AND is_delete = 0 AND status = 1 ORDER BY sort
                    """
                    cursor.execute(sql_query_tutor)
                    data_tutor = MysqlOper.get_query_result(cursor)
                    dict_each["tutor"] = []
                    for row in data_tutor:
                        dict_tutor = {}
                        dict_tutor["user_id"] = row.get("user_id")
                        dict_tutor["me_id"] = row.get("me_id")
                        dict_tutor["tutor_id"] = row.get("tutor_id")
                        dict_tutor["avatar"] = row.get("avatar")
                        dict_tutor["character_name"] = row.get(
                            "character_name")
                        dict_tutor["greeting"] = row.get("greeting")
                        dict_tutor["implicit_hint"] = row.get("implicit_hint")
                        dict_tutor["introduction"] = row.get("introduction")
                        dict_tutor["influence"] = row.get("influence")
                        dict_tutor["document"] = row.get("document")
                        dict_tutor["image"] = row.get("image")
                        dict_tutor["website"] = row.get("website")
                        dict_tutor["is_copied"] = row.get("is_copied")
                        dict_tutor["sort"] = row.get("sort")
                        dict_tutor["status"] = row.get("status")
                        dict_tutor["is_built_in"] = row.get("is_built_in")
                        dict_each["tutor"].append(dict_tutor)
                    if len(dict_each["tutor"]) < 8:
                        num_empty_dicts = 8 - len(dict_each["tutor"])

                        for _ in range(num_empty_dicts):
                            dict_each["tutor"].append({})
                    ret_data.append(dict_each)

                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class BatchBindTutor(APIView):
    @swagger_auto_schema(
        operation_id="151",
        tags=["V5.5"],
        operation_summary="批量绑定导师",
        operation_description="批量绑定导师",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["me_ids"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
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
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="User ID"
                                    )
                                },
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
        me_id = data.get("me_id")
        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_query = f"""
                    SELECT tutor_id, avatar,character_name,greeting, implicit_hint, introduction,
                       influence,document, image, website, sort,  is_copied,  extend  FROM {settings.DEFAULT_DB}.sva_tutor
                    WHERE  is_delete = 0 AND is_built_in = 1 LIMIT 8
                    """

        ret_data = []

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                results = MysqlOper.get_query_result(cursor)
                for each in results:
                    dict_data = {}
                    tutor_id = each.get("tutor_id")
                    avatar = each.get("avatar")
                    character_name = each.get("character_name")
                    greeting = each.get("greeting")
                    implicit_hint = each.get("implicit_hint")
                    introduction = each.get("introduction")
                    influence = each.get("influence")
                    document = each.get("document")
                    image = each.get("image")
                    website = each.get("website")
                    is_copied = each.get("is_copied")
                    sort = each.get("sort")
                    extend = each.get("extend")
                    dict_data["me_id"] = me_id
                    dict_data["tutor_id"] = tutor_id
                    dict_data["avatar"] = avatar
                    dict_data["character_name"] = character_name
                    dict_data["greeting"] = greeting
                    dict_data["implicit_hint"] = implicit_hint
                    dict_data["introduction"] = introduction
                    dict_data["influence"] = influence
                    dict_data["document"] = document
                    dict_data["image"] = image
                    dict_data["website"] = website
                    dict_data["is_copied"] = is_copied
                    dict_data["extend"] = extend
                    dict_data["sort"] = sort
                    ret_data.append(dict_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        if ret_data:
            sql_batch_create = f"""
                INSERT INTO {settings.DEFAULT_DB}.sva_tutor
                (user_id, me_id, tutor_id, avatar, character_name, greeting, implicit_hint, introduction, influence, document, image, website, sort, extend, is_built_in, is_copied, is_delete)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            print(sql_batch_create)
            try:
                with connection.cursor() as cursor:
                    cursor.executemany(
                        sql_batch_create,
                        [
                            (
                                user_id,
                                data["me_id"],
                                data["tutor_id"],
                                data["avatar"],
                                data["character_name"],
                                data["greeting"],
                                data["implicit_hint"],
                                data["introduction"],
                                data["influence"],
                                data["document"],
                                data["image"],
                                data["website"],
                                data["sort"],
                                data["extend"],
                                0,
                                data["is_copied"],
                                0,
                            )
                            for data in ret_data
                        ],
                    )
                    rowcount = cursor.rowcount

                    print(rowcount)
                    print("rowcountrowcountrowcountrowcount")
                    if rowcount == len(ret_data):
                        code = RET.OK
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
        else:
            code = RET.DB_ERR
            message = Language.get(code)
            return CstResponse(code=code, message=message)


class PromptManage(APIView):
    @swagger_auto_schema(
        operation_id="152",
        tags=["V6.4.3"],
        operation_summary="提示词创建",
        operation_description="提示词创建",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "prompt_content"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "prompt_content": openapi.Schema(type=openapi.TYPE_STRING, description="提示词内容"),
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
                        )
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
        worker_id = 100003
        data = request.data
        user_id = data.get("user_id")
        prompt = data.get('prompt_content')
        prompt_id = get_distributed_id(worker_id=worker_id)
        if not user_id or not prompt:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_create = f"""
                    INSERT INTO {settings.DEFAULT_DB}.cp_prompt (user_id, prompt_content, prompt_id)
                    VALUES ({user_id},'{prompt}', {prompt_id})
                    """

        print(sql_create)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_create)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
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
        operation_id="153",
        tags=["V6.4.3"],
        operation_summary="获取提示次列表",
        operation_description="获取提示次列表",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="用户ID",
                required=True
            ),
        ],
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
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="User ID",

                                    ),
                                    "prompt_content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="提示词内容",

                                    ),
                                    "prompt_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="提示词id",

                                    )
                                },
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
    def get(self, request):
        data = request.query_params
        user_id = data.get("user_id")

        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_query = f"""

            SELECT user_id, prompt_content, prompt_id FROM {settings.DEFAULT_DB}.cp_prompt WHERE is_delete = 0 AND user_id = {user_id}
            ORDER BY created_at
       """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                query_data = MysqlOper.get_query_result(cursor)
                ret_data = []
                for each in query_data:
                    each_data = {}
                    each_data['user_id'] = user_id
                    each_data['prompt_content'] = each.get('prompt_content')
                    each_data['prompt_id'] = each.get('prompt_id')
                    ret_data.append(each_data)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="154",
        tags=["V6.4.3"],
        operation_summary="提示词删除",
        operation_description="提示词删除",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "prompt_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, description="用户ID"),
                "prompt_id": openapi.Schema(type=openapi.TYPE_STRING, description="提示词ID"),
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
                        )
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
    def put(self, request):
        data = request.data
        user_id = data.get("user_id")
        prompt_id = data.get('prompt_id')
        if not user_id or not prompt_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        sql_update = f"""
                    UPDATE  {settings.DEFAULT_DB}.cp_prompt  SET is_delete = 1 WHERE user_id = {user_id} AND prompt_id = {prompt_id}
                    """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
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


class MatchContext(APIView):

    def post(self, request):
        data = request.data

        me_id = data.get('me_id')
        tutor_id = data.get('tutor_id')
        question_content = data.get('question_content')
        user_id = data.get('user_id')

        sql_get = (
            f"SELECT * FROM {settings.DEFAULT_DB}.sva_me WHERE me_id = '{me_id}' "
            f"  AND is_delete = 0"
        )

        if tutor_id:
            sql_get = (
                f"SELECT * FROM {settings.DEFAULT_DB}.sva_tutor WHERE tutor_id = '{tutor_id}' "
                f" AND is_delete = 0"
            )

        print(sql_get)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get)
                db_data = MysqlOper.get_query_result(cursor)[0]
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        where_condition = {"me_id": me_id} if me_id else {"tutor_id": tutor_id}
        embeded_db_content = settings.APP.query(question_content, citations=True, where=where_condition)

        if not embeded_db_content:
            prompts = ''
        else:
            if tutor_id:
                prompts = generate_structured_prompt_tutor(
                    question_content,
                    db_data.get('character_name'),
                    db_data.get('greeting'),
                    db_data.get('implicit_hint'),
                    db_data.get('introduction'),
                    db_data.get('influence'),
                    embeded_db_content[0][0] if embeded_db_content else ''
                )
            else:
                prompts = generate_structured_prompt(question_content,
                                                     db_data.get('name'),
                                                     db_data.get('age'),
                                                     db_data.get('occupation'),
                                                     db_data.get('transferring_gender'),
                                                     db_data.get('transferring_education'),
                                                     db_data.get('major'),
                                                     db_data.get('hobbies'),
                                                     db_data.get('region'),
                                                     db_data.get('greeting'),
                                                     db_data.get('relationship_status'),
                                                     db_data.get('dream'),
                                                     db_data.get('income'),
                                                     db_data.get('image_description'),
                                                     db_data.get('extend'),
                                                     embeded_db_content[0][0] if embeded_db_content else '')
        # redis存储，方便对话接口去拿
        r = get_redis_connection("prompts")
        prompts_to_redis_name = "agent"
        prompts_to_redis_key = tutor_id if tutor_id else me_id
        prompts_to_redis_value = json.dumps({"prompts": prompts}, ensure_ascii=False)
        r.hset(prompts_to_redis_name, prompts_to_redis_key, prompts_to_redis_value)
        ret_data = {
            'prompt': prompts
        }

        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=ret_data)
