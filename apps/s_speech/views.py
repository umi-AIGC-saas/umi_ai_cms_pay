from utils.gadgets import gadgets
from utils.cst_class import CstException, CstResponse
from language.language_pack import RET, Language
from rest_framework.views import APIView
from rest_framework import status
from openai import OpenAI
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import connection
from django.conf import settings
import json
import logging
import math
import os
import traceback
import uuid

import requests

from utils.OSS.tooss import Tooss

logger = logging.getLogger("view")


class SpeechToText(APIView):
    @swagger_auto_schema(
        operation_id="1001",
        tags=["语音对讲"],
        operation_summary="语音对讲 - 转录文本 - 暂时弃用",
        operation_description="语音对讲 - 转录文本 - 暂时弃用",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["speech_url"],
            properties={
                "speech_url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文件网络地址"
                ),
                "speech_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="文件名称"
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户 id"
                ),
                "session_code": openapi.Schema(
                    type=openapi.TYPE_STRING, description="会话 id"
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
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "session_code": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="会话 ID."
                                ),
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户 id."
                                ),
                                "user_speech_url": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户语音文件地址."
                                ),
                                "user_text": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="用户语音文件对应文本内容.",
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
        speech_url = data.get("speech_url")
        speech_name = data.get("speech_name")
        user_id = data.get("user_id")
        session_code = data.get("session_code")

        if not speech_url or not speech_name or not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            raise CstException(code=code, message=message)

        try:
            speech_file = gadgets.download_file(
                speech_url, f"./static/{speech_name}")
            print(speech_file)
            if os.path.exists(f"./static/{speech_name}"):
                print("xxxxxxxxxx")
            else:
                print("dddddddddd")
            if not speech_file or not os.path.exists(
                    f"./static/{speech_name}"):
                print(222222)
                code = RET.NETWORK_ERROR
                message = Language.get(code)
                raise CstException(code=code, message=message)
        except Exception:
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        try:
            audio_file = open(f"./static/{speech_name}", "rb")
            with OpenAI(base_url='https://openai.qiheweb.com/v1',
                        api_key="sk-aWlXvBleYj9FiZZ176A4B2Be9aBc4dBcA70a0d498eFf7e18") as client:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    prompt="这是一段用户使用手机录制的录音文件",
                )

        except Exception:
            os.remove(f"./static/{speech_name}")
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        if not transcript:
            os.remove(f"./static/{speech_name}")
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        try:
            insert_to_sql = (
                f"INSERT INTO {settings.DEFAULT_DB}.s_speech (user_id, session_code, llm_speech_url, "
                f" user_speech_url) VALUES (%s, %s, %s, %s) ")

            insert_params = [user_id, session_code, "", speech_url]
            with connection.cursor() as cursor:
                cursor.execute(insert_to_sql, insert_params)

                if cursor.rowcount > 0:
                    ret_data = {
                        "session_code": session_code,
                        "user_id": user_id,
                        "user_speech_url": speech_url,
                        "user_text": transcript,
                    }
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(
                        code=code, message=message, data=ret_data)
                else:
                    code = RET.NETWORK_ERROR
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
        except Exception:
            os.remove(f"./static/{speech_name}")
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)


class TextToSpeech(APIView):
    @swagger_auto_schema(
        operation_id="1003",
        tags=["语音对讲"],
        operation_summary="语音对讲 - 转录语音",
        operation_description="语音对讲 - 转录语音",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "llm_answer": openapi.Schema(
                    type=openapi.TYPE_STRING, description="大模型返回答案"
                ),
                "character": openapi.Schema(type=openapi.TYPE_STRING, description="音色"),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户 id"
                ),
                "session_code": openapi.Schema(
                    type=openapi.TYPE_STRING, description="会话 ID"
                ),
                "speech_order": openapi.Schema(
                    type=openapi.TYPE_STRING, description="在session_code下的第几次对话"
                ),
                "is_advanced": openapi.Schema(
                    type=openapi.TYPE_STRING, description="是否高级版"
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
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "session_code": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="会话id."
                                ),
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户 id."
                                ),
                                "user_speech_url": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户语音文件地址."
                                ),
                                "user_text": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="用户语音文件对应文本内容.",
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
        llm_answer = data.get("llm_answer")
        character = data.get("character", "alloy")
        user_id = data.get("user_id")
        session_code = data.get("session_code")
        speech_order = data.get("speech_order")
        is_advanced = data.get("is_advanced")

        speech_data = {
            "character": character,
            "llm_answer": llm_answer,
            "user_id": user_id,
            "session_code": session_code,
            "speech_order": speech_order
        }
        try:
            speech_url = gadgets.create_speech(speech_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        if not speech_url:

            code = RET.NETWORK_ERROR
            message = Language.get(code)
            raise CstException(code=code, message=message)

        if not is_advanced:
            # 扣费, 确保取余向上
            cost_current_speech = math.ceil(
                ((len(llm_answer) + 999) // 1000) * 4.2)
        else:
            cost_current_speech = math.ceil(
                ((len(llm_answer) + 999) // 1000) * 127.8)
        consume_hashrate = gadgets.operate_hashrates(
            user_id=user_id, hashrate=cost_current_speech, scene=2
        )

        insert_to_sql = (
            f"INSERT INTO {settings.DEFAULT_DB}.s_speech (user_id, session_code, llm_speech_url, "
            f" user_speech_url) VALUES (%s, %s, %s, %s) ")

        insert_params = [user_id, session_code, speech_url, ""]
        with connection.cursor() as cursor:
            cursor.execute(insert_to_sql, insert_params)

            if cursor.rowcount > 0 and consume_hashrate:
                ret_data = {
                    "session_code": session_code,
                    "user_id": user_id,
                    "llm_answer": llm_answer,
                    "llm_speech_url": speech_url,
                }
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
            else:
                code = RET.NETWORK_ERROR
                message = Language.get(code)
                return CstResponse(code=code, message=message)

    @swagger_auto_schema(
        operation_id="1002",
        tags=["语音对讲"],
        operation_summary="语音对讲 - 获取形象",
        operation_description="语音对讲 - 获取形象",
        manual_parameters=[],
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
                                "name_eng": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="英文名称, 传值用"
                                ),
                                "name_cn": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="中文名称, 展示用"
                                ),
                                "sound_url": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="声音地址"
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
    def get(self, request):

        dict_character = [
            {
                "name_eng": "onyx",
                "name_cn": "玛瑙-成熟男声",
                "sound_url": "static/speech_character/onyx.wav",
            },
            {
                "name_eng": "nova",
                "name_cn": "新星-温柔女声",
                "sound_url": "static/speech_character/nova.wav",
            },
            {
                "name_eng": "alloy",
                "name_cn": "金属风-标准男声",
                "sound_url": "static/speech_character/alloy.wav",
            },
            {
                "name_eng": "echo",
                "name_cn": "回音-冷静男声",
                "sound_url": "static/speech_character/echo.wav",
            },
            {
                "name_eng": "fable",
                "name_cn": "故事-标准女声",
                "sound_url": "static/speech_character/fable.wav",
            },
            {
                "name_eng": "shimmer",
                "name_cn": "微光-成熟女声",
                "sound_url": "static/speech_character/shimmer.wav",
            },
        ]
        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=dict_character)
