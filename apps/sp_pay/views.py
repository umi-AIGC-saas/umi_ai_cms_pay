import ast
import datetime
import json
import logging
import math
import random
import time
import traceback
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import List
from urllib.parse import parse_qs

import requests
from django.conf import settings
from django.db import connection, connections, transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_extensions.cache.decorators import cache_response

from language.language_pack import RET, Language
from utils.cst_class import CstException, CstResponse
from utils.distributed_id_generator.get_id import get_distributed_id
from utils.gadgets import CstKeyConstructor, gadgets
from utils.json_datetime import DateTimeEncoder
from utils.my_decorators import (ExperienceCardRejectSecPurchase,
                                 ValidateAmount)
from utils.payment.alipay import AliPay
from utils.payment.wechat_pay import (get_pay_sign, get_sign,
                                      query_payment_status, trans_dict_to_xml,
                                      trans_xml_to_dict, wxpay)
from utils.scripts.query_order_status import QueryOrderStatusQueue
from utils.serializers import QuestionsSetManageSerializer
from utils.sql_oper import MysqlOper

logger = logging.getLogger("view")


class Introduction(APIView):
    """
    文档相关参数说明
    """

    @swagger_auto_schema(
        operation_id="1",
        tags=["文档相关"],
        operation_summary="获取接口相关参数",
        operation_description="This endpoint retrieves the status codes and descriptions for the API.",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "HTTP_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="HTTP状态码及其描述",
                                    properties={
                                        "20000": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="成功"
                                        ),
                                        "50000": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="服务器异常",
                                        ),
                                        "50001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="数据库异常",
                                        ),
                                        "30001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="订单生成失败",
                                        ),
                                        "30002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="支付宝二维码生成失败",
                                        ),
                                        "30003": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="微信支付二维码生成失败",
                                        ),
                                        "30004": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="微信支付回调失败",
                                        ),
                                        "30005": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="支付宝回调失败",
                                        ),
                                        "30006": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="订单总金额有误",
                                        ),
                                        "30007": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="支付结果查询错误",
                                        ),
                                        "30008": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="支付成功"
                                        ),
                                        "30009": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="待付款"
                                        ),
                                        "30010": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="链路追踪捕获",
                                        ),
                                        "30011": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="订单过期"
                                        ),
                                    },
                                ),
                                "ORDER_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="订单状态",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="待付款"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="已付款"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="已取消"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="已过期"
                                        ),
                                    },
                                ),
                                "READ_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="已读状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="未读"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="已读"
                                        ),
                                    },
                                ),
                                "INFO_TYPES": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="输入框/文本框映射",
                                    properties={
                                        "438600126748678": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="Textarea",
                                        ),
                                        "438260526168070": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="Tag"
                                        ),
                                        "438257788905478": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="Select",
                                        ),
                                        "438257565440006": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="Input",
                                        ),
                                        "438257535715334": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="CheckBox",
                                        ),
                                    },
                                ),
                                "AROUSEL_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="已读状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="否"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="是"
                                        ),
                                    },
                                ),
                                "REVIEW_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="审核状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="审核中"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="审核通过"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="拒绝"
                                        ),
                                    },
                                ),
                                "QUESTION_CONFIG_TYPES": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="附加类型映射",
                                    properties={
                                        "Dropdown": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="下拉菜单"
                                        ),
                                        "Progress": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="进度条"
                                        ),
                                        "Tag": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="标签"
                                        ),
                                        "ColorPicker": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="颜色选择器",
                                        ),
                                        "Rate": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="评分"
                                        ),
                                        "DateTimePicker": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="日期时间选择器",
                                        ),
                                        "DatePicker": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="日期选择器",
                                        ),
                                        "TimePicker": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="时间选择器",
                                        ),
                                        "Slider": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="滑块"
                                        ),
                                        "Switch": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="开关"
                                        ),
                                        "Select": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="选择器"
                                        ),
                                        "InputNumber": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="计数器"
                                        ),
                                        "Input": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="输入框"
                                        ),
                                        "CheckBox": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="多选框"
                                        ),
                                        "Radio": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="单选框"
                                        ),
                                    },
                                ),
                                "MESSAGE_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="已读状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="未定义"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="使用中"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="暂停"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="删除"
                                        ),
                                    },
                                ),
                                "PAYMENT_STATUS": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="支付状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="待付款"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="成功"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="退款"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="失败"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="失效"
                                        ),
                                    },
                                ),
                                "LIFE_ASSISTANT_ROLE_PLAY": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="生活助理&角色扮演",
                                    properties={
                                        "1000": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属行业ID",
                                        ),
                                        "1001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属行业ID",
                                        ),
                                        "2001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属职业ID",
                                        ),
                                        "2002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属职业ID",
                                        ),
                                        "3001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属二级职业ID",
                                        ),
                                        "3002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属二级职业ID",
                                        ),
                                        "4001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属从业时间ID",
                                        ),
                                        "4002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属从业时间ID",
                                        ),
                                        "5001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属技能等级ID",
                                        ),
                                        "5002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属技能等级ID",
                                        ),
                                        "6001": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="生活助理默认所属模块ID",
                                        ),
                                        "6002": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="角色扮演默认所属模块ID",
                                        ),
                                    },
                                ),
                                "PICTURES": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="支付状态",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="其他"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="公众号"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="客服"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="小程序"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="联系客服"
                                        ),
                                    },
                                ),
                                "COOP_TYPE": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="合作类型",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="其他"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="城市运营商",
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="源码定制"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="api接口",
                                        ),
                                    },
                                ),
                                "OPERATE_TYPE": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="操作目标类型",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="AI35_count",
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="AI40_count",
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="dalle_2_count",
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="baidu_drawing_count",
                                        ),
                                    },
                                ),
                                "PRODUCTIONS": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        enum=[
                                            "gpt35",
                                            "gpt40",
                                            "baidu_drawing",
                                            "dalle2",
                                        ],
                                    ),
                                    description="产品列表",
                                ),
                                "USER_TYPE": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="游客类型",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="游客"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="注册用户"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="VIP"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="SVIP"
                                        ),
                                    },
                                ),
                                "PAYMENT_METHOD": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="支付方式",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="支付宝"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="微信"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="卡密"
                                        ),
                                    },
                                ),
                                "MESSAGE_TYPE": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="消息类型",
                                    properties={
                                        "0": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="系统消息"
                                        ),
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="站内信"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="资讯"
                                        ),
                                    },
                                ),
                                "PROD_CATE": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="支付方式",
                                    properties={
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="会员类"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="分销"
                                        ),
                                        "5": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="加油包"
                                        ),
                                    },
                                ),
                                "EDUCATION": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="学历",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="博士"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="硕士"
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="本科"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="大专"
                                        ),
                                        "5": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="高中"
                                        ),
                                        "6": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="初中"
                                        ),
                                        "7": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="小学"
                                        ),
                                        "8": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="其他"
                                        ),
                                    },
                                ),
                                "ACTION": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="赠送行为标记",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="每天登陆"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="转发"
                                        ),
                                    },
                                ),
                                "GENDER": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="性别",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="男"
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="女"
                                        ),
                                    },
                                ),
                                "PROD_ID_NAME_MAP": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="产品id映射",
                                    properties={
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="三年会员"
                                        ),
                                        "4": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="年会员"
                                        ),
                                        "5": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="季会员"
                                        ),
                                        "6": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="月会员"
                                        ),
                                        "7": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="周会员"
                                        ),
                                        "9": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="游客试用"
                                        ),
                                        "10": openapi.Schema(
                                            type=openapi.TYPE_STRING, description="注册试用"
                                        ),
                                    },
                                ),
                                "ALIPAY_METHOD": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="支付宝支付方式",
                                    properties={
                                        "1": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="direct_pay",
                                        ),
                                        "2": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="wap_pay",
                                        ),
                                        "3": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="app_pay",
                                        ),
                                    },
                                ),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def get(self):
        HTTP_STATUS = {
            20000: "成功",
            50000: "服务器异常",
            50001: "数据库异常",
            30001: "订单生成失败",
            30002: "支付宝二维码生成失败",
            30003: "微信支付二维码生成失败",
            30004: "微信支付回调失败",
            30005: "支付宝回调失败",
            30006: "订单总金额有误",
            30007: "支付结果查询错误",
            30008: "支付成功",
            30009: "待付款",
            30010: "链路追踪捕获",
            30011: "订单过期",
        }
        PRODS = ["gpt35", "gpt40", "baidu_drawing", "dalle2"]

        EDUCATION = {
            1: "博士",
            2: "硕士",
            3: "本科",
            4: "大专",
            5: "高中",
            6: "初中",
            7: "小学",
            8: "其他",
        }
        LIFE_ASSISTANT_ROLE_PLAY = {
            1000: "生活助理默认所属行业ID",
            1001: "角色扮演默认所属行业ID",
            2001: "生活助理默认所属职业ID",
            2002: "角色扮演默认所属职业ID",
            3001: "生活助理默认所属二级职业ID",
            3002: "角色扮演默认所属二级职业ID",
            4001: "生活助理默认所属从业时间ID",
            4002: "角色扮演默认所属从业时间ID",
            5001: "生活助理默认所属技能等级ID",
            5002: "角色扮演默认所属技能等级ID",
            6001: "生活助理默认所属模块ID",
            6002: "角色扮演默认所属模块ID",
        }

        ORDER_STATUS = ({1: "待付款", 2: "已付款", 3: "已取消", 4: "已过期"},)
        PROD_CATE = {3: "会员类商品", 4: "分销会员", 5: "加油包"}
        REVIEW_STATUS = {
            0: "审核中",
            1: "通过",
            2: "拒绝",
        }
        MESSAGE_TYPE = {
            0: "系统消息",
            1: "站内信",
            2: "资讯",
        }
        PAYMENT_STATUS = {
            0: "待付款",
            1: "成功",
            2: "退款",
            3: "失败",
            4: "失效",
        }
        GENDER = {"1": "男", "2": "女"}
        COOP_TYPE = {
            0: "其他",
            1: "城市运营商",
            2: "源码定制",
            3: "api接口",
        }

        INFO_TYPES = {
            438600126748678: "Textarea",
            438260526168070: "Tag",
            438257788905478: "Select",
            438257565440006: "Input",
            438257535715334: "CheckBox",
        }
        ALIPAY_METHOD = {1: "direct_pay", 2: "wap_pay", 3: "app_pay"}

        USER_TYPE = {
            1: "游客",
            2: "注册用户",
            3: "VIP",
            4: "SVIP",
        }
        PICTURES = {
            0: "其他",
            1: "公众号",
            2: "客服",
            3: "小程序",
            4: "联系客服",
        }
        OPERATE_TARGET = {
            "1": "AI35_count",
            "2": "AI40_count",
            "3": "dalle_2_count",
            "4": "baidu_drawing_count",
        }

        PAYMENT_METHOD = {1: "支付宝", 2: "微信", 3: "卡密兑换"}

        ACTION = {1: "每天登陆", 2: "转发"}

        PROD_ID_NAME_MAP = {
            3: "三年会员",
            4: "年会员",
            5: "季会员",
            6: "月会员",
            7: "周会员",
            9: "游客试用",
            10: "注册试用",
        }

        RET_DATA = {
            "HTTP_STATUS": HTTP_STATUS,
            "ORDER_LIST_STATUS": ORDER_STATUS,
            "PAYMENT_STATUS": PAYMENT_STATUS,
            "ALIPAY_METHOD": ALIPAY_METHOD,
            "USER_TYPE": USER_TYPE,
            "OPERATE_TARGET": OPERATE_TARGET,
            "PAYMENT_METHOD": PAYMENT_METHOD,
            "ACTION": ACTION,
            "PROD_ID_NAME_MAP": PROD_ID_NAME_MAP,
            "COOP_TYPE": COOP_TYPE,
            "PICTURES": PICTURES,
            "LIFE_ASSISTANT_ROLE_PLAY": LIFE_ASSISTANT_ROLE_PLAY,
            "PRODUCTION": PRODS,
            "PROD_CATE": PROD_CATE,
            "REVIEW_STATUS": REVIEW_STATUS,
            "INFO_TYPES": INFO_TYPES,
            "EDUCATION": EDUCATION,
            "GENDER": GENDER,
            "MESSAGE_TYPE": MESSAGE_TYPE,
        }

        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=RET_DATA)


class ProductsList(APIView):
    @swagger_auto_schema(
        operation_id="2",
        tags=["v3.1"],
        operation_summary="获取商品列表",
        operation_description="This endpoint retrieves the list of orders of a user based on the given filters.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["prod_cate_id"],
            properties={
                "prod_cate_id": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="商品种类id",
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of products.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "prod_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="商品id"
                                    ),
                                    "prod_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="商品名称"
                                    ),
                                    "prod_valid": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="商品有效期"
                                    ),
                                    "prod_details": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        description="The details of the product.",
                                        properties={
                                            "version_3_5": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="3.5版本详情",
                                            ),
                                            "version_4_0": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="4.0版本详情",
                                            ),
                                        },
                                    ),
                                    "prod_origin_price": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="商品原价"
                                    ),
                                    "prod_price": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="商品当前价格"
                                    ),
                                    "prod_cate_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="商品种类id"
                                    ),
                                    "continuous_annual_sub_price": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="连续订阅价格"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        prod_cate_id = data.get("prod_cate_id")

        if len(prod_cate_id) == 1:
            prod_cate_id = "({})".format(str(prod_cate_id[0]))
        else:
            prod_cate_id = tuple(prod_cate_id)
        # sql_fetch_prod = f"SELECT prod_id, prod_name, prod_description, prod_details, prod_origin_price, prod_price,continuous_annual_sub_price, prod_cate_id FROM {settings.DEFAULT_DB}." \
        #                  f"pp_products WHERE prod_cate_id in {prod_cate_id} AND is_show = 1  ORDER BY prod_price DESC"

        sql_fetch_prod = (
            f"SELECT prod_id, prod_name, prod_description, prod_details,prod_rules, "
            f"prod_origin_price, prod_price,continuous_annual_sub_price, prod_cate_id, "
            f" directed_hashrate,universal_hashrate,  hashrate FROM {settings.DEFAULT_DB}."
            f" pp_products WHERE prod_cate_id in {prod_cate_id} AND is_show = 1 ORDER BY prod_price DESC")

        logger.info(sql_fetch_prod)

        ret_data = defaultdict(list)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_prod)
                query_data = MysqlOper.get_query_result(cursor)
                for each_prod in query_data:
                    prod_data = {}
                    prod_id = each_prod.get("prod_id")
                    prod_name = each_prod.get("prod_name")
                    prod_desc = each_prod.get("prod_description")
                    prod_rules = each_prod.get("prod_rules")
                    prod_details = each_prod.get("prod_details")
                    prod_origin_price = each_prod.get("prod_origin_price")
                    prod_price = each_prod.get("prod_price")
                    prod_cate_id = each_prod.get("prod_cate_id")
                    continuous_annual_sub_price = each_prod.get(
                        "continuous_annual_sub_price"
                    )
                    directed_hashrate = each_prod.get("directed_hashrate")
                    hashrate = each_prod.get("hashrate")
                    universal_hashrate = each_prod.get("universal_hashrate")

                    prod_desc_object = defaultdict(dict)
                    if prod_desc and "|" in prod_desc:
                        prod_desc = prod_desc.split("|")
                        prod_desc_object["count"] = prod_desc[0].strip()
                        prod_desc_object["valid"] = prod_desc[1].strip()
                    else:
                        prod_desc_object = {}

                    prod_details_object = defaultdict(dict)

                    if int(prod_cate_id) == 3:
                        prod_details = prod_details.split("|")
                        prod_details_object["version_3_5"] = prod_details[0]
                        prod_details_object["version_4_0"] = prod_details[1]
                    else:
                        prod_details_object["value"] = prod_details

                    prod_data["prod_id"] = prod_id
                    prod_data["prod_name"] = prod_name
                    prod_data["prod_desc"] = prod_desc_object
                    prod_data["prod_details"] = prod_details_object
                    prod_data["prod_origin_price"] = prod_origin_price
                    prod_data["prod_price"] = prod_price
                    prod_data["prod_rules"] = prod_rules
                    prod_data["prod_points"] = str(
                        math.ceil(
                            float(prod_origin_price) *
                            settings.POINTS_UNIT))
                    prod_data["prod_cate_id"] = prod_cate_id
                    prod_data["hashrate"] = hashrate
                    prod_data["directed_hashrate"] = directed_hashrate
                    prod_data["universal_hashrate"] = universal_hashrate
                    prod_data["prod_cate_id"] = prod_cate_id
                    prod_data[
                        "continuous_annual_sub_price"
                    ] = continuous_annual_sub_price
                    ret_data[prod_cate_id].append(prod_data)

            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)

            raise CstException(code=code, message=message)


# 旧版订单中心，暂时废弃
# class OrdersList(APIView):
#
#     def __init__(self):
#         super(OrdersList, self).__init__()
#
#     @swagger_auto_schema(
#         operation_id='3',
#         tags=['v3.1'],
#         operation_summary='获取订单列表',
#         operation_description='该接口根据给定的筛选条件获取用户的订单列表。',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['user_id', 'prod_cate_id'],
#             properties={
#                 'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID。'),
#                 'page_index': openapi.Schema(type=openapi.TYPE_INTEGER, description='页码索引。'),
#                 'page_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='每页数量。'),
#                 'order_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='订单ID。'),
#                 'status': openapi.Schema(type=openapi.TYPE_STRING, description='订单状态。'),
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='成功',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='成功代码。'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='成功消息。'),
#                         'data': openapi.Schema(
#                             type=openapi.TYPE_ARRAY,
#                             description='订单列表。',
#                             items=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     'order_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='订单ID。'),
#                                     'source': openapi.Schema(type=openapi.TYPE_INTEGER, description='来源。'),
#                                     'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='订单总金额。'),
#                                     'payment_method': openapi.Schema(type=openapi.TYPE_STRING, description='订单支付方式。'),
#                                     'prod_cate_id': openapi.Schema(type=openapi.TYPE_STRING, description='订单支付方式。'),
#                                     'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='商品种类。'),
#                                     'expire_at': openapi.Schema(type=openapi.TYPE_STRING, description='有效期。'),
#                                     'status': openapi.Schema(type=openapi.TYPE_STRING, description='订单状态。'),
#                                     'quantity': openapi.Schema(type=openapi.TYPE_STRING, description='数量。'),
#                                     'prod_name': openapi.Schema(type=openapi.TYPE_STRING, description='产品名称。'),
#                                 }
#                             )
#                         ),
#                         'total': openapi.Schema(type=openapi.TYPE_INTEGER, description='订单总数。'),
#                     }
#                 )
#             ),
#             status.HTTP_400_BAD_REQUEST: openapi.Response(
#                 description='错误的请求',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='错误代码。'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='错误消息。'),
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='服务器内部错误',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='错误代码。'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='错误消息。'),
#                     }
#                 )
#             )
#         }
#     )
#     def post(self, request):
#
#         data = request.data
#         user_id = data.get('user_id')
#         page_index = data.get('page_index')
#         page_count = data.get('page_count')
#         order_id = data.get('order_id')
#         status = data.get('status')
#
#         prod_cate_id = data.get('prod_cate_id', '[3,5,6]')
#
#         if not prod_cate_id:
#             code = RET.PARAM_MISSING
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)
#
#         prod_cate_id = ast.literal_eval(prod_cate_id)
#
#         sql_fetch_orders_raw = f"SELECT a.order_id, a.source,oi.price, b.prod_name,b.prod_id, b.prod_cate_id, b.prod_cate_id, a.total_amount, c.payment_method" \
#                                f", a.created_at, a.status, oi.quantity, d.expire_at " \
#                                f" FROM {settings.DEFAULT_DB}.po_orders AS a LEFT JOIN {settings.DEFAULT_DB}.po_orders_items " \
#                                f" AS oi ON a.order_id = oi.order_id LEFT JOIN " \
#                                f" {settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id LEFT JOIN " \
#                                f" {settings.DEFAULT_DB}.pp_payments AS c ON a.order_id = c.order_id LEFT JOIN " \
#                                f" {settings.DEFAULT_DB}.pm_membership AS d ON a.order_id = d.order_id " \
#                                f" WHERE a.is_delete = 0 AND a.user_id = {user_id} AND oi.is_delete = 0  "
#
#         sql_fetch_orders_total_raw = f"SELECT COUNT(a.order_id)  AS total " \
#                                      f"FROM {settings.DEFAULT_DB}.po_orders AS a LEFT JOIN {settings.DEFAULT_DB}.po_orders_items " \
#                                      f"AS oi ON a.order_id = oi.order_id LEFT JOIN " \
#                                      f"{settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id LEFT JOIN " \
#                                      f"{settings.DEFAULT_DB}.pp_payments AS c ON a.order_id = c.order_id LEFT JOIN " \
#                                      f"{settings.DEFAULT_DB}.pm_membership d  ON a.order_id = d.order_id " \
#                                      f" WHERE a.is_delete = 0 AND a.user_id = {user_id} " \
#                                      f" AND a.is_delete = 0 AND b.is_delete = 0 AND c.is_delete = 0 AND oi.is_delete = 0 "
#         if status:
#             if status == '0':
#                 sql_fetch_orders_raw = sql_fetch_orders_raw
#             else:
#                 sql_fetch_orders_raw += f"AND  a.status = {status} "
#                 sql_fetch_orders_total_raw += f"AND  a.status = {status} "
#         else:
#             sql_fetch_orders_raw = sql_fetch_orders_raw
#
#         if order_id:
#             sql_fetch_orders_raw += f" AND a.order_id = {order_id} "
#             sql_fetch_orders_total_raw += f" AND a.order_id = {order_id} "
#
#         if prod_cate_id:
#             sql_fetch_orders_raw += f" AND oi.prod_cate_id in {tuple(prod_cate_id)} "
#             sql_fetch_orders_total_raw += f" AND oi.prod_cate_id in  {tuple(prod_cate_id)} "
#
#         sql_fetch_orders_raw += "ORDER BY created_at DESC "
#
#         if page_count is not None:
#             sql_fetch_orders_raw += " LIMIT " + str(page_count)
#
#             if page_index is not None:
#                 row_index = int(int(page_index) - 1) * int(page_count)
#                 sql_fetch_orders_raw += " OFFSET " + str(row_index)
#
#         logger.info(sql_fetch_orders_raw)
#
#         list_orders: List[defaultdict] = []
#
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute(sql_fetch_orders_total_raw)
#                 query_total_data = MysqlOper.get_query_result(cursor)
#                 query_total = query_total_data[0].get('total')
#             with connection.cursor() as cursor:
#                 cursor.execute(sql_fetch_orders_raw)
#                 query_data = MysqlOper.get_query_result(cursor)
#                 for each_order in query_data:
#                     order_data = defaultdict(dict)
#                     order_id = each_order.get('order_id')
#                     source = each_order.get('source')
#                     prod_id = each_order.get('prod_id')
#                     prod_cate_id = each_order.get('prod_cate_id')
#                     total_amount = each_order.get('total_amount')
#                     quantity = each_order.get('quantity')
#                     prod_price = each_order.get('price')
#                     payment_method = each_order.get('payment_method')
#                     created_at = each_order.get('created_at')
#                     status = each_order.get('status')
#                     prod_name = each_order.get('prod_name')
#
#                     if int(prod_cate_id) == 3:
#
#                         expire_at = each_order.get('expire_at')
#
#                     else:
#                         r_usage = get_redis_connection('usage')
#
#                         package_key = f"package:{user_id}:{prod_id}:{order_id}"
#                         expire_at = r_usage.hget(package_key, 'expire_at')
#
#                     if expire_at:
#                         expire_at = float(expire_at)
#                         expire_at = datetime.datetime.fromtimestamp(expire_at)
#                         expire_at = expire_at.strftime("%Y-%m-%d %H:%M:%S")
#                     else:
#                         expire_at = ''
#
#                     order_data['order_id'] = order_id
#                     order_data['source'] = source
#                     order_data['prod_price'] = prod_price
#                     order_data['total_amount'] = total_amount
#                     order_data['payment_method'] = payment_method
#                     order_data['prod_cate_id'] = prod_cate_id
#                     order_data['created_at'] = created_at
#                     order_data['status'] = status
#                     order_data['prod_name'] = prod_name
#                     order_data['expire_at'] = expire_at
#                     order_data['quantity'] = quantity
#                     list_orders.append(order_data)
#
#             code = RET.OK
#             message = Language.get(code)
#             return CstResponse(code=code, message=message, data=list_orders, total=query_total)
#         except Exception:
#             code = RET.DB_ERR
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)
#
#     @swagger_auto_schema(
#         operation_id='4',
#         tags=['删除订单【新】'],
#         operation_summary='删除订单',
#         operation_description='This endpoint deletes one or multiple orders based on the provided order IDs.',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['order_ids'],
#             properties={
#                 'order_ids': openapi.Schema(
#                     type=openapi.TYPE_ARRAY,
#                     description='A list of order IDs to be deleted.',
#                     items=openapi.Items(type=openapi.TYPE_STRING)
#                 ),
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Success',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='A success code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='A success message.'),
#                         'data': openapi.Schema(
#                             type=openapi.TYPE_ARRAY,
#                             description='A list of deleted order details.',
#                             items=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     'order_ids': openapi.Schema(
#                                         type=openapi.TYPE_ARRAY,
#                                         description='A list of deleted order IDs.',
#                                         items=openapi.Items(type=openapi.TYPE_STRING)
#                                     ),
#                                 }
#                             )
#                         )
#                     }
#                 )
#             ),
#             status.HTTP_400_BAD_REQUEST: openapi.Response(
#                 description='Bad Request',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='An error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='An error message.'),
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Internal Server Error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='An error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='An error message.'),
#                     }
#                 )
#             )
#         }
#     )
#     def delete(self, request):
#         data = request.data
#         order_ids = data.get('order_ids')
#
#         try:
#             with connection.cursor() as cursor:
#                 if isinstance(order_ids, list):
#                     # 批量删除
#                     order_ids_str = "', '".join(order_ids)
#                     # 更新po_orders、po_orders_items、pp_payments表的is_delete字段为1
#                     sql_update = f"UPDATE {settings.DEFAULT_DB}.po_orders AS o " \
#                                  f"JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON o.order_id = oi.order_id " \
#                                  f"JOIN {settings.DEFAULT_DB}.pp_payments AS p ON o.order_id = p.order_id " \
#                                  f"SET o.is_delete = 1, oi.is_delete = 1, p.is_delete = 1 " \
#                                  f"WHERE o.order_id IN ('{order_ids_str}')"
#
#                 elif isinstance(order_ids, str):
#                     # 单个删除
#                     # 更新po_orders、po_orders_items、pp_payments表的is_delete字段为1
#                     sql_update = f"UPDATE {settings.DEFAULT_DB}.po_orders AS o " \
#                                  f"JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON o.order_id = oi.order_id " \
#                                  f"JOIN {settings.DEFAULT_DB}.pp_payments AS p ON o.order_id = p.order_id " \
#                                  f"SET o.is_delete = 1, oi.is_delete = 1, p.is_delete = 1 " \
#                                  f"WHERE o.order_id = '{order_ids}'"
#
#                 cursor.execute(sql_update)
#                 rowcount = cursor.rowcount
#                 ret_data = {
#                     'oder_ids': order_ids
#                 }
#
#                 logger.error(sql_update)
#
#                 if rowcount > 0:
#
#                     code = RET.OK
#                     message = Language.get(code)
#                     return CstResponse(code=code, message=message, data=[ret_data])
#                 else:
#                     code = RET.DB_ERR
#                     message = Language.get(code)
#                     trace = str(traceback.format_exc())
#                     logger.error(trace)
#                     raise CstException(code=code, message=message)
#
#         except Exception:
#             code = RET.DB_ERR
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)


class OrdersList(APIView):
    def __init__(self):
        super(OrdersList, self).__init__()

    @swagger_auto_schema(
        operation_id="3",
        tags=["v3.1"],
        operation_summary="获取订单列表",
        operation_description="该接口根据给定的筛选条件获取用户的订单列表。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "prod_cate_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID。"
                ),
                "page_index": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="页码索引。"
                ),
                "page_count": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="每页数量。"
                ),
                "order_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="订单ID。"
                ),
                "status": openapi.Schema(type=openapi.TYPE_STRING, description="订单状态。"),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="订单列表。",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="订单ID。"
                                    ),
                                    "source": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="来源。"
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="订单总金额。"
                                    ),
                                    "payment_method": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单支付方式。"
                                    ),
                                    "prod_cate_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单支付方式。"
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="商品种类。"
                                    ),
                                    "expire_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="有效期。"
                                    ),
                                    "status": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单状态。"
                                    ),
                                    "quantity": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="数量。"
                                    ),
                                    "prod_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="产品名称。"
                                    ),
                                },
                            ),
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="订单总数。"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误的请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data
        user_id = data.get("user_id")
        page_index = data.get("page_index")
        page_count = data.get("page_count")
        order_id = data.get("order_id")
        status = data.get("status")

        prod_cate_id = data.get("prod_cate_id", [3,6])

        prod_cate_id = [str(each) for each in prod_cate_id]

        prod_cate_id = ','.join(prod_cate_id)

        if not prod_cate_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


        sql_fetch_orders_raw = (
            f"SELECT a.order_id, a.source,oi.price, b.prod_name,b.prod_id, b.prod_cate_id, "
            f"b.prod_cate_id, b.valid_period_days,  a.total_amount, c.payment_method"
            f", a.created_at, a.status, oi.quantity, d.expire_at "
            f" FROM {settings.DEFAULT_DB}.po_orders AS a LEFT JOIN {settings.DEFAULT_DB}.po_orders_items "
            f" AS oi ON a.order_id = oi.order_id LEFT JOIN "
            f" {settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id LEFT JOIN "
            f" {settings.DEFAULT_DB}.pp_payments AS c ON a.order_id = c.order_id LEFT JOIN "
            f" {settings.DEFAULT_DB}.pm_membership AS d ON a.order_id = d.order_id "
            f" WHERE a.is_delete = 0 AND a.user_id = {user_id} AND oi.is_delete = 0  ")

        sql_fetch_orders_total_raw = (
            f"SELECT COUNT(a.order_id)  AS total "
            f"FROM {settings.DEFAULT_DB}.po_orders AS a LEFT JOIN {settings.DEFAULT_DB}.po_orders_items "
            f"AS oi ON a.order_id = oi.order_id LEFT JOIN "
            f"{settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id LEFT JOIN "
            f"{settings.DEFAULT_DB}.pp_payments AS c ON a.order_id = c.order_id LEFT JOIN "
            f"{settings.DEFAULT_DB}.pm_membership d  ON a.order_id = d.order_id "
            f" WHERE a.is_delete = 0 AND a.user_id = {user_id} "
            f" AND a.is_delete = 0 AND b.is_delete = 0 AND c.is_delete = 0 AND oi.is_delete = 0 ")
        if status:
            if status == "0":
                sql_fetch_orders_raw = sql_fetch_orders_raw
            else:
                sql_fetch_orders_raw += f"AND  a.status = {status} "
                sql_fetch_orders_total_raw += f"AND  a.status = {status} "
        else:
            sql_fetch_orders_raw = sql_fetch_orders_raw

        if order_id:
            sql_fetch_orders_raw += f" AND a.order_id = {order_id} "
            sql_fetch_orders_total_raw += f" AND a.order_id = {order_id} "

        if prod_cate_id:
            sql_fetch_orders_raw += f" AND oi.prod_cate_id in ({prod_cate_id}) "
            sql_fetch_orders_total_raw += (
                f" AND oi.prod_cate_id in ({prod_cate_id}) "
            )

        sql_fetch_orders_raw += "ORDER BY created_at DESC "

        if page_count is not None:
            sql_fetch_orders_raw += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_fetch_orders_raw += " OFFSET " + str(row_index)

        logger.info(sql_fetch_orders_raw)

        list_orders: List[defaultdict] = []

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_orders_total_raw)
                query_total_data = MysqlOper.get_query_result(cursor)
                query_total = query_total_data[0].get("total")
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_orders_raw)
                query_data = MysqlOper.get_query_result(cursor)
                for each_order in query_data:
                    order_data = defaultdict()
                    order_id = each_order.get("order_id")
                    source = each_order.get("source")
                    valid_period_days = each_order.get("valid_period_days")
                    prod_cate_id = each_order.get("prod_cate_id")
                    total_amount = each_order.get("total_amount")
                    quantity = each_order.get("quantity")
                    prod_price = each_order.get("price")
                    payment_method = each_order.get("payment_method")
                    created_at = each_order.get("created_at")
                    status = each_order.get("status")
                    prod_name = each_order.get("prod_name")
                    from datetime import datetime, timedelta

                    date_obj = datetime.strptime(
                        created_at, "%Y-%m-%d %H:%M:%S")
                    date_obj = date_obj + \
                               timedelta(days=int(valid_period_days))

                    expire_at = date_obj.strftime("%Y-%m-%d %H:%M:%S")

                    order_data["order_id"] = order_id
                    order_data["source"] = source
                    order_data["prod_price"] = prod_price
                    order_data["total_amount"] = total_amount
                    order_data["payment_method"] = payment_method
                    order_data["prod_cate_id"] = prod_cate_id
                    order_data["created_at"] = created_at
                    order_data["status"] = status
                    order_data["prod_name"] = prod_name
                    order_data["expire_at"] = expire_at
                    order_data["quantity"] = quantity
                    list_orders.append(order_data)

            code = RET.OK
            message = Language.get(code)
            return CstResponse(
                code=code, message=message, data=list_orders, total=query_total
            )
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="4",
        tags=["删除订单【新】"],
        operation_summary="删除订单",
        operation_description="This endpoint deletes one or multiple orders based on the provided order IDs.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_ids"],
            properties={
                "order_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="A list of order IDs to be deleted.",
                    items=openapi.Items(type=openapi.TYPE_STRING),
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of deleted order details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "order_ids": openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        description="A list of deleted order IDs.",
                                        items=openapi.Items(type=openapi.TYPE_STRING),
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def delete(self, request):
        data = request.data
        order_ids = data.get("order_ids")

        try:
            with connection.cursor() as cursor:
                if isinstance(order_ids, list):
                    # 批量删除
                    order_ids_str = "', '".join(order_ids)
                    # 更新po_orders、po_orders_items、pp_payments表的is_delete字段为1
                    sql_update = (
                        f"UPDATE {settings.DEFAULT_DB}.po_orders AS o "
                        f"JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON o.order_id = oi.order_id "
                        f"JOIN {settings.DEFAULT_DB}.pp_payments AS p ON o.order_id = p.order_id "
                        f"SET o.is_delete = 1, oi.is_delete = 1, p.is_delete = 1 "
                        f"WHERE o.order_id IN ('{order_ids_str}')")

                elif isinstance(order_ids, str):
                    # 单个删除
                    # 更新po_orders、po_orders_items、pp_payments表的is_delete字段为1
                    sql_update = (
                        f"UPDATE {settings.DEFAULT_DB}.po_orders AS o "
                        f"JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON o.order_id = oi.order_id "
                        f"JOIN {settings.DEFAULT_DB}.pp_payments AS p ON o.order_id = p.order_id "
                        f"SET o.is_delete = 1, oi.is_delete = 1, p.is_delete = 1 "
                        f"WHERE o.order_id = '{order_ids}'")

                cursor.execute(sql_update)
                rowcount = cursor.rowcount
                ret_data = {"oder_ids": order_ids}

                logger.error(sql_update)

                if rowcount > 0:

                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class MembershipManage(APIView):
    @swagger_auto_schema(
        operation_id="5",
        tags=["获取用户会员信息"],
        operation_summary="获取用户会员信息",
        operation_description="该方法获取用户的会员信息，包括会员到期日期、会员等级名称和ID。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="会员信息列表。",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "expire_date": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="会员到期日期。"
                                    ),
                                    "level_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="会员等级名称。"
                                    ),
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户ID。"
                                    ),
                                    "level_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="会员等级ID。"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data
        user_id = data.get("user_id")

        # SQL query to retrieve membership information from the database
        sql_member_info = (
            f"SELECT FROM_UNIXTIME({settings.DEFAULT_DB}.pm_membership.expire_at) AS expire_date, "
            f"{settings.DEFAULT_DB}.pm_membership_levels.level_name, "
            f"{settings.DEFAULT_DB}.pm_membership_levels.level_id "
            f"FROM {settings.DEFAULT_DB}.pm_membership JOIN {settings.DEFAULT_DB}.pm_membership_levels "
            f"ON {settings.DEFAULT_DB}.pm_membership.points >= {settings.DEFAULT_DB}.pm_membership_levels.points_threshold "
            f"WHERE {settings.DEFAULT_DB}.pm_membership.user_id = {user_id} AND {settings.DEFAULT_DB}.pm_membership.is_delete = 0 "
            f"AND {settings.DEFAULT_DB}.pm_membership.user_id = {user_id} "
            f"AND {settings.DEFAULT_DB}.pm_membership.status =1 AND {settings.DEFAULT_DB}.pm_membership.is_delete = 0 "
            f"AND {settings.DEFAULT_DB}.pm_membership_levels.is_delete = 0 "
            f" ORDER BY {settings.DEFAULT_DB}.pm_membership.expire_at  DESC  LIMIT 1 ")

        logger.info(sql_member_info)

        member_info = {
            "expire_date": "",
            "level_name": "",
            "user_id": "",
            "level_id": "",
            "status": False,
        }

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_member_info)
                query_data = MysqlOper.get_query_result(cursor)
                for each_member in query_data:
                    expire_date = each_member.get("expire_date")
                    level_name = each_member.get("level_name")
                    level_id = each_member.get("level_id")
                    member_info["expire_date"] = expire_date
                    member_info["level_name"] = level_name
                    member_info["user_id"] = user_id
                    member_info["level_id"] = level_id

            code = RET.OK
            message = Language.get(code)
            # 暂时没有会员概念了,返回空结构体, 后期改回来的话 这边返回member_info
            return CstResponse(code=code, message=message, data={})
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            # Log the error traceback for debugging purposes
            trace = str(traceback.format_exc())
            logger.error(trace)
            # Raise a custom exception with the error message and status code
            raise CstException(code=code, message=message)


class NewVisitorUser(APIView):
    @swagger_auto_schema(
        operation_id="6",
        tags=["创建新访问者用户，【废弃】"],
        operation_summary="创建新访问者用户",
        operation_description="该端点用于新访客用户进来赋予次数和token。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
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
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息"
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="返回数据的总数"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="数据列表",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户ID"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        user_id = request.data.get("user_id")

        # default user 5 counts added
        sql_insert = f"INSERT INTO {settings.DEFAULT_DB}.os_statistics (user_id, tokens, count) VALUES ({user_id}, 0, 5)"

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_insert)
                rowcount = cursor.rowcount

                dict_data = defaultdict(dict)

                if rowcount > 0:
                    dict_data["user_id"] = user_id
            code = RET.OK
            message = Language.get(code)
            return CstResponse(
                code=code,
                message=message,
                total=1,
                data=[dict_data])
        except Exception:
            # if error occured, catch it and throw
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class FormSheetAlipay(APIView):
    """
    支付宝表单支付视图。
    """

    @swagger_auto_schema(
        operation_id="7",
        tags=["v3.1"],
        operation_summary="创建支付宝支付订单",
        operation_description="该接口用于创建支付宝支付订单。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "prod_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品ID"
                ),
                "prod_cate_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品cate id"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商品名称"
                ),
                "total_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="总金额"
                ),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="商品价格"),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品数量"
                ),
                "method": openapi.Schema(type=openapi.TYPE_INTEGER, description="支付方式"),
            },
            required=[
                "user_id",
                "prod_id",
                "prod_cate_id",
                "prod_name",
                "total_amount",
                "price",
                "quantity",
                "method",
            ],
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="产品列表",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "pay_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="支付链接"
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="总金额"
                                    ),
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单ID"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    @ValidateAmount(param={"db": settings.DEFAULT_DB, "logger": logger})
    @transaction.atomic()
    @csrf_exempt
    @ExperienceCardRejectSecPurchase(
        param={"db": settings.DEFAULT_DB, "logger": logger}
    )
    def post(self, request):
        worker_id = 1000
        data = request.data
        user_id = data.get("user_id")
        prod_id = data.get("prod_id")
        prod_name = data.get("prod_name")
        total_amount = data.get("total_amount")
        price = data.get("price")
        model_name = data.get("model_name", '')
        live_code = data.get("live_code", '')
        quantity = data.get("quantity")
        method = data.get("method")
        prod_cate_id = data.get("prod_cate_id")
        order_id = get_distributed_id(worker_id=worker_id)

        # 新增判断来源
        source = request.META.get("HTTP_SOURCE", "")

        if not method:
            method = 1
        order_status = 1

        validate_amount = request.__dict__.get("validate_amount_pass")
        #
        if not validate_amount:
            code = RET.ORDER_AMOUNT_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        save_id = transaction.savepoint()

        unpaid_sql_order = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders (order_id, source, user_id,  total_amount, status,prod_cate_id ) "
            f" VALUES ({order_id}, '{source}', {user_id}, {total_amount}, {order_status}, {prod_cate_id})")

        logger.error(unpaid_sql_order)

        try:
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_order)
                unpaid_row_count_order = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_orders_items = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders_items (order_id, prod_id, quantity, price, prod_cate_id, model_name, live_code) "
            f" VALUES ({order_id}, {prod_id},{quantity}, {price}, {prod_cate_id}, '{model_name}', '{live_code}')")

        try:
            logger.info(unpaid_sql_orders_items)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_orders_items)
                unpaid_row_orders_items = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_payments = (
            f"INSERT INTO {settings.DEFAULT_DB}.pp_payments (order_id, user_id, amount, status, payment_method, pay_data) "
            f" VALUES ({order_id}, {user_id},{total_amount}, 0, 1, '')")

        try:
            logger.info(unpaid_sql_payments)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_payments)
                unpaid_row_sql_payments = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        if (unpaid_row_count_order +
                unpaid_row_orders_items +
                unpaid_row_sql_payments == 3):

            if int(method) == 1:
                try:
                    query_param = AliPay().direct_pay(
                        subject=prod_name,
                        out_trade_no=order_id,
                        total_amount=total_amount,
                    )

                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)
                    raise CstException(code=code, message=message)
            elif int(method) == 2:
                try:
                    query_param = AliPay().h5_pay(
                        subject=prod_name,
                        out_trade_no=order_id,
                        total_amount=total_amount,
                    )
                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)
                    raise CstException(code=code, message=message)
            else:
                try:
                    query_param = AliPay().app_pay(
                        subject=prod_name,
                        out_trade_no=order_id,
                        total_amount=total_amount,
                    )
                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)
                    raise CstException(code=code, message=message)

            pay_url = "https://openapi.alipay.com/gateway.do?{}".format(
                query_param)

            pre_pay_sql_payments = f"""
                        UPDATE {settings.DEFAULT_DB}.pp_payments
                        SET pay_data = %s
                        WHERE order_id = %s
                    """

            params = [pay_url, order_id]
            try:
                with connection.cursor() as cursor:
                    cursor.execute(pre_pay_sql_payments, params)
                    pr_pay_row_sql_payments = cursor.rowcount

                    if pr_pay_row_sql_payments > 0:
                        code = RET.OK
                        message = Language.get(code)
                        ret_data = {
                            "pay_url": pay_url,
                            "total_amount": total_amount,
                            "order_id": order_id,
                        }
                        transaction.savepoint_commit(save_id)
                        return CstResponse(
                            code=code, message=message, data=[ret_data])
                    else:
                        code = RET.ALIPAY_PAY_QR_FAIL
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        raise CstException(code=code, message=message)

            except Exception:
                code = RET.ORDER_CREATE_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)
                raise CstException(code=code, message=message)

        else:

            code = RET.ALIPAY_PAY_QR_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


# 旧版暂时废弃
# class UpdateOrderAlipay(APIView):
#
#     @swagger_auto_schema(
#         operation_id='10',
#         tags=['v3.1'],
#         operation_summary='更新支付宝订单',
#         operation_description='This endpoint updates the status of an order paid through Alipay.',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['sign', 'out_trade_no', 'trade_no'],
#             properties={
#                 'sign': openapi.Schema(type=openapi.TYPE_STRING, description='Alipay签名'),
#                 'out_trade_no': openapi.Schema(type=openapi.TYPE_STRING, description='商户订单号'),
#                 'trade_no': openapi.Schema(type=openapi.TYPE_STRING, description='支付宝交易号'),
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Success',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='成功代码'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='成功信息'),
#                     }
#                 )
#             ),
#             status.HTTP_400_BAD_REQUEST: openapi.Response(
#                 description='Bad Request',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='错误代码'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='错误信息'),
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Internal Server Error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='错误代码'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='错误信息'),
#                     }
#                 )
#             )
#         }
#     )
#     @transaction.atomic()
#     def post(self, request):
#
#         body_str = request.body.decode('utf-8')
#         post_data = parse_qs(body_str)
#         post_dict = {}
#         for k, v in post_data.items():
#             post_dict[k] = v[0]
#         save_id = transaction.savepoint()
#         sign = post_dict.pop('sign', None)
#         status = AliPay().verify(post_dict, sign)
#
#         if status:
#             order_id = post_dict.get('out_trade_no')
#             pay_id = post_dict.get('trade_no')
#
#             update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {pay_id} WHERE order_id = {order_id}"
#             update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1 WHERE order_id = {order_id}"
#
#             try:
#                 with connection.cursor() as cursor:
#                     cursor.execute(update_payment)
#                     update_payment_rowcount = cursor.rowcount
#
#                 with connection.cursor() as cursor:
#                     cursor.execute(update_order)
#                     update_order_rowcount = cursor.rowcount
#
#                 if update_payment_rowcount + update_order_rowcount == 2:
#
#                     # 查询用户购买的产品类别
#                     sql_get_prod_cate = f"SELECT a.user_id, a.prod_cate_id, b.prod_id, b.quantity,b.price, a.total_amount FROM {settings.DEFAULT_DB}.po_orders a " \
#                                         f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id " \
#                                         f" WHERE  a.order_id = {order_id}"
#
#                     logger.info(sql_get_prod_cate)
#
#                     try:
#                         with connection.cursor() as cursor:
#                             cursor.execute(sql_get_prod_cate)
#                             prod_cate_data = MysqlOper.get_query_result(cursor)
#
#                             if prod_cate_data:
#                                 user_id = prod_cate_data[0].get('user_id')
#                                 prod_id = prod_cate_data[0].get('prod_id')
#                                 prod_cate_id = prod_cate_data[0].get('prod_cate_id')
#                                 quantity = prod_cate_data[0].get('quantity')
#                                 price = prod_cate_data[0].get('price')
#                                 total_amount = prod_cate_data[0].get('total_amount')
#                             else:
#                                 code = RET.DB_ERR
#                                 message = Language.get(code)
#                                 trace = str(traceback.format_exc())
#                                 logger.error(trace)
#                                 transaction.savepoint_rollback(save_id)
#                                 raise CstException(code=code, message=message)
#                     except Exception:
#                         code = RET.DB_ERR
#                         message = Language.get(code)
#                         trace = str(traceback.format_exc())
#                         logger.error(trace)
#                         transaction.savepoint_rollback(save_id)
#                         raise CstException(code=code, message=message)
#
#                     config_prod_redis = get_redis_connection('config')
#                     cates_dict = config_prod_redis.get('config:products:cate')
#                     cates_dict = json.loads(cates_dict)
#                     current_cate = cates_dict.get(prod_cate_id)
#
#                     print(cates_dict)
#                     print('llllllllll')
#                     print(current_cate)
#                     if current_cate == "member":
#                         insert_extend = gadgets.insert_new_member(order_id=order_id, conn=connection, pay=True)
#                     elif current_cate == "package":
#                         insert_extend = gadgets.insert_data_plus(user_id=user_id, prod_id=prod_id, order_id=order_id,
#                                                                  quantity=quantity, price=price)
#                     elif current_cate == "universal":
#                         insert_extend = gadgets.insert_data_plus(user_id=user_id, prod_id=prod_id, order_id=order_id,
#                                                                  quantity=quantity, price=price)
#                     elif current_cate == "reseller":
#                         insert_extend = True
#                     else:
#                         insert_extend = ''
#                     print('zzzzzzzzzzzzzzzzzzzzzzz')
#                     print(prod_cate_id)
#                     # 分销逻辑
#                     if int(prod_cate_id) == 4:
#                         print('kkkkkkkkkkkkk')
#                         response_upgrade_level = gadgets.extend_upgrade_distribution_level(user_id)
#                         response_pay_commission = gadgets.extend_pay_commission(user_id, order_id, total_amount, '1')
#
#                         if response_upgrade_level and response_pay_commission:
#                             call_distribution = True
#                         else:
#                             call_distribution = False
#                         call_out_video = True
#                         call_clone = True
#                         call_submit_voice = True
#
#                     else:
#                         if int(prod_cate_id) in [7, 8]:
#                             call_distribution = True
#                             insert_extend = True
#                             call_out_video = gadgets.update_out_video_status(order_id)
#                             call_clone = gadgets.update_clone_status(order_id)
#                             call_submit_voice = gadgets.submit_customized_voice(order_id)
#
#                         else:
#                             response_pay_commission = gadgets.extend_pay_commission(user_id, order_id, total_amount,
#                                                                                     '0')
#                             if response_pay_commission:
#                                 call_distribution = True
#                             else:
#                                 call_distribution = False
#
#                             call_submit_voice = True
#                             call_out_video = True
#                             call_clone = True
#                     print(prod_cate_id)
#                     print(insert_extend)
#                     print(call_distribution)
#                     print(call_submit_voice)
#                     print(call_out_video)
#                     print(call_clone)
#                     print('fffffffff')
#
#                     if insert_extend and call_distribution and call_out_video and call_clone and call_submit_voice:
#                         transaction.savepoint_commit(save_id)
#                         return HttpResponse("success")
#                     else:
#                         code = RET.DB_ERR
#                         message = Language.get(code)
#                         trace = str(traceback.format_exc())
#                         logger.error(trace)
#                         transaction.savepoint_rollback(save_id)
#
#                         raise CstException(code=code, message=message)
#                 else:
#
#                     code = RET.ALIPAY_PAY_CALLBACK_FAIL
#                     message = Language.get(code)
#                     trace = str(traceback.format_exc())
#                     logger.error(trace)
#                     transaction.savepoint_rollback(save_id)
#
#                     raise CstException(code=code, message=message)
#
#             except Exception:
#                 code = RET.ALIPAY_PAY_CALLBACK_FAIL
#                 message = Language.get(code)
#                 trace = str(traceback.format_exc())
#                 logger.error(trace)
#                 transaction.savepoint_rollback(save_id)
#
#                 raise CstException(code=code, message=message)
#         else:
#
#             code = RET.ALIPAY_PAY_CALLBACK_FAIL
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             transaction.savepoint_rollback(save_id)
#
#             raise CstException(code=code, message=message)


class UpdateOrderAlipay(APIView):
    @swagger_auto_schema(
        operation_id="10",
        tags=["v3.1"],
        operation_summary="更新支付宝订单",
        operation_description="This endpoint updates the status of an order paid through Alipay.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sign", "out_trade_no", "trade_no"],
            properties={
                "sign": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Alipay签名"
                ),
                "out_trade_no": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商户订单号"
                ),
                "trade_no": openapi.Schema(
                    type=openapi.TYPE_STRING, description="支付宝交易号"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功信息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
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
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    def post(self, request):

        body_str = request.body.decode("utf-8")
        post_data = parse_qs(body_str)
        post_dict = {}
        for k, v in post_data.items():
            post_dict[k] = v[0]
        save_id = transaction.savepoint()
        sign = post_dict.pop("sign", None)
        status = AliPay().verify(post_dict, sign)

        if status:
            order_id = post_dict.get("out_trade_no")
            pay_id = post_dict.get("trade_no")

            update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {pay_id} WHERE order_id = {order_id}"
            update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1 WHERE order_id = {order_id}"

            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_payment)
                    update_payment_rowcount = cursor.rowcount

                with connection.cursor() as cursor:
                    cursor.execute(update_order)
                    update_order_rowcount = cursor.rowcount

                if update_payment_rowcount + update_order_rowcount == 2:

                    # 查询用户购买的产品类别
                    sql_get_prod_cate = (
                        f"SELECT a.user_id, a.prod_cate_id, b.prod_id, b.quantity,b.price, a.total_amount FROM {settings.DEFAULT_DB}.po_orders a "
                        f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id "
                        f" WHERE  a.order_id = {order_id}")

                    logger.info(sql_get_prod_cate)

                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_get_prod_cate)
                            prod_cate_data = MysqlOper.get_query_result(cursor)

                            if prod_cate_data:
                                user_id = prod_cate_data[0].get("user_id")
                                prod_id = prod_cate_data[0].get("prod_id")
                                prod_cate_id = prod_cate_data[0].get(
                                    "prod_cate_id")
                                quantity = prod_cate_data[0].get("quantity")
                                price = prod_cate_data[0].get("price")
                                total_amount = prod_cate_data[0].get(
                                    "total_amount")
                            else:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                transaction.savepoint_rollback(save_id)
                                raise CstException(code=code, message=message)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        raise CstException(code=code, message=message)

                    user_active_data = {"user_id": user_id}

                    user_active_req = requests.post(
                        url=settings.SERVER_BILL_URL
                            + ":"
                            + settings.SERVER_BILL_PORT
                            + settings.IS_ACTIVE_ADDRESS,
                        data=user_active_data,
                    )
                    if user_active_req.status_code == 200:
                        user_active_req_data = json.loads(user_active_req.text)
                        if user_active_req_data.get("code") == 20000:
                            user_is_active = user_active_req_data.get("data")
                        else:
                            user_is_active = False
                    else:
                        user_is_active = False

                    if user_is_active:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_ADDRESS
                        )
                    else:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_RENEW
                        )

                    insert_member_success = False
                    insert_package_success = False
                    call_distribution = False
                    call_submit_voice = False
                    call_out_video = False
                    call_clone = False
                    call_huoshan_sound = False
                    # 会员类别，写入会员有效期等数据和写入算力值&算力值有效期
                    if int(prod_cate_id) == 3:
                        insert_member_config = gadgets.insert_new_member(
                            order_id=order_id, conn=connection, pay=True
                        )

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": prod_id,
                            "quantity": quantity,
                            "prod_cate_id": prod_cate_id,
                        }

                        insert_member_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        if insert_member_hashrate_req.status_code == 200:
                            insert_member_hashrate_data = json.loads(
                                insert_member_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                insert_member_hashrate = True
                            else:
                                insert_member_hashrate = False
                        else:
                            insert_member_hashrate = False

                        if insert_member_config and insert_member_hashrate:
                            insert_member_success = True
                            insert_package_success = True
                        else:
                            insert_member_success = False
                            insert_package_success = False
                    # 流量包写入算力值和算力值有效期
                    elif int(prod_cate_id) == 6:

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": prod_id,
                            "quantity": quantity,
                            "prod_cate_id": prod_cate_id,
                        }
                        insert_package_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        if insert_package_hashrate_req.status_code == 200:
                            insert_member_hashrate_data = json.loads(
                                insert_package_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                insert_package_success = True
                                insert_member_success = True
                    else:
                        # 非会员和流量包外的其他逻辑
                        insert_member_success = True
                        insert_package_success = True

                    # 分销逻辑
                    if int(prod_cate_id) == 4:
                        response_upgrade_level = (
                            gadgets.extend_upgrade_distribution_level(user_id)
                        )
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "1")

                        if response_upgrade_level and response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False
                        # insert_member_success = True
                        # insert_package_success = True
                        call_out_video = True
                        call_clone = True
                        call_submit_voice = True
                        call_huoshan_sound = True

                    elif int(prod_cate_id) in [7, 8, 9]:
                        if int(prod_cate_id) in [7, 8]:
                            call_distribution = True
                            # insert_member_success = True
                            # insert_package_success = True
                            call_out_video = gadgets.update_out_video_status(
                                order_id)
                            call_clone = gadgets.update_clone_status(order_id)
                            call_submit_voice = gadgets.submit_customized_voice(
                                order_id)
                            call_huoshan_sound = True
                        elif int(prod_cate_id) == 9:
                            call_huoshan_sound_req = gadgets.call_huoshan_sound_clone(order_id)
                            if call_huoshan_sound_req:
                                call_huoshan_sound = True
                                call_submit_voice = True
                                call_out_video = True
                                call_clone = True
                            else:
                                call_huoshan_sound = False
                                call_submit_voice = True
                                call_out_video = True
                                call_clone = True
                        else:
                            response_pay_commission = gadgets.extend_pay_commission(
                                user_id, order_id, total_amount, "0")
                            if response_pay_commission:
                                call_distribution = True
                            else:
                                call_distribution = False

                            call_submit_voice = True
                            call_out_video = True
                            call_clone = True
                            call_huoshan_sound = True

                    logger.info("insert_package_success: ", insert_package_success)
                    logger.info("insert_member_success: ", insert_member_success)
                    logger.info("call_distribution:", call_distribution)
                    logger.info("call_submit_voice:", call_submit_voice)
                    logger.info("call_out_video:", call_out_video)
                    logger.info("call_clone:", call_clone)
                    logger.info("call_huoshan_sound:", call_huoshan_sound)
                    if (
                            insert_package_success
                            and insert_member_success
                            and call_distribution
                            and call_out_video
                            and call_clone
                            and call_submit_voice
                            and call_huoshan_sound
                    ):
                        transaction.savepoint_commit(save_id)
                        return HttpResponse("success")
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)

                        raise CstException(code=code, message=message)
                else:

                    code = RET.ALIPAY_PAY_CALLBACK_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)

                    raise CstException(code=code, message=message)

            except Exception:
                code = RET.ALIPAY_PAY_CALLBACK_FAIL
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)

                raise CstException(code=code, message=message)
        else:

            code = RET.ALIPAY_PAY_CALLBACK_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)

            raise CstException(code=code, message=message)


class QueryOrderStatus(APIView):
    @swagger_auto_schema(
        operation_id="60",
        tags=["v3.1"],
        operation_summary="主动查询订单状态",
        operation_description="主动查询订单状态.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sign", "out_trade_no", "trade_no"],
            properties={
                "sign": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Alipay签名"
                ),
                "out_trade_no": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商户订单号"
                ),
                "trade_no": openapi.Schema(
                    type=openapi.TYPE_STRING, description="支付宝交易号"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功信息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
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
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    def post(self, request):
        our_trade_no = request.data.get("order_id")

        query_order = AliPay().api_alipay_trade_query(
            trade_no=None, out_trade_no=our_trade_no
        )

        status_code = query_order.get("code")
        status_msg = query_order.get("msg")

        save_id = transaction.savepoint()
        print(query_order)
        print("query_orderquery_orderquery_order")
        if int(status_code) == 10000 and status_msg == "Success":
            order_id = our_trade_no
            pay_id = query_order.get("trade_no")

            update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {pay_id} WHERE order_id = {order_id}"
            update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1  WHERE order_id = {order_id}"

            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_payment)
                    update_payment_rowcount = cursor.rowcount

                with connection.cursor() as cursor:
                    cursor.execute(update_order)
                    update_order_rowcount = cursor.rowcount

                if update_payment_rowcount + update_order_rowcount == 2:

                    # 查询用户购买的产品类别
                    sql_get_prod_cate = (
                        f"SELECT a.user_id, a.prod_cate_id, b.prod_id, b.quantity, a.total_amount, b.price FROM {settings.DEFAULT_DB}.po_orders a "
                        f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id "
                        f" WHERE  a.order_id = {order_id}")

                    logger.info(sql_get_prod_cate)

                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_get_prod_cate)
                            prod_cate_data = MysqlOper.get_query_result(cursor)

                            if prod_cate_data:
                                user_id = prod_cate_data[0].get("user_id")
                                prod_id = prod_cate_data[0].get("prod_id")
                                prod_cate_id = prod_cate_data[0].get(
                                    "prod_cate_id")
                                quantity = prod_cate_data[0].get("quantity")
                                price = prod_cate_data[0].get("price")
                                total_amount = prod_cate_data[0].get(
                                    "total_amount")
                            else:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                transaction.savepoint_rollback(save_id)
                                raise CstException(code=code, message=message)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        raise CstException(code=code, message=message)

                    config_prod_redis = get_redis_connection("config")
                    cates_dict = config_prod_redis.get("config:products:cate")
                    cates_dict = json.loads(cates_dict)
                    current_cate = cates_dict.get(prod_cate_id)

                    logger.error(current_cate)
                    logger.error(cates_dict)
                    if current_cate == "member":
                        insert_extend = gadgets.insert_new_member(
                            order_id=order_id, conn=connection, pay=True
                        )
                    elif current_cate == "package":
                        insert_extend = gadgets.insert_data_plus(
                            user_id=user_id,
                            prod_id=prod_id,
                            order_id=order_id,
                            quantity=quantity,
                            price=price,
                        )
                    elif current_cate == "universal":
                        insert_extend = gadgets.insert_data_plus(
                            user_id=user_id,
                            prod_id=prod_id,
                            order_id=order_id,
                            quantity=1,
                            price=price,
                        )
                    elif current_cate == "reseller":
                        insert_extend = True

                    else:
                        insert_extend = ""
                    # 分销逻辑
                    if int(prod_cate_id) == 4:
                        response_upgrade_level = (
                            gadgets.extend_upgrade_distribution_level(user_id)
                        )
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "1")

                        if response_upgrade_level and response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False

                    else:
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "0")
                        if response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False

                    logger.error(insert_extend)
                    logger.error(call_distribution)
                    if insert_extend and call_distribution:
                        transaction.savepoint_commit(save_id)
                        return HttpResponse("success")
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)

                        raise CstException(code=code, message=message)
                else:

                    code = RET.ALIPAY_PAY_CALLBACK_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)

                    raise CstException(code=code, message=message)

            except Exception:
                print(traceback.format_exc())
                code = RET.ALIPAY_PAY_CALLBACK_FAIL
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)

                raise CstException(code=code, message=message)
        else:

            code = RET.ALIPAY_PAY_CALLBACK_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)

            raise CstException(code=code, message=message)


class FormSheetWechat(APIView):
    @swagger_auto_schema(
        operation_id="8",
        tags=["v3.1"],
        operation_summary="处理微信支付表单",
        operation_description="该方法处理表单微信支付PC提交订单。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID。"
                ),
                "prod_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品ID。"
                ),
                "prod_cate_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品cate id。"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商品名称。"
                ),
                "total_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="订单总金额。"
                ),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="商品价格。"),
                "trade_type": openapi.Schema(
                    type=openapi.TYPE_STRING, description="交易类型。"
                ),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品数量。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="返回的数据列表。",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "pay_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="支付链接。"
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="订单总金额。"
                                    ),
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="订单ID。"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    @ValidateAmount(param={"db": settings.DEFAULT_DB, "logger": logger})
    @transaction.atomic()
    @ExperienceCardRejectSecPurchase(
        param={"db": settings.DEFAULT_DB, "logger": logger}
    )
    def post(self, request):
        workder_id = 1001
        data = request.data
        user_id = data.get("user_id")

        prod_id = data.get("prod_id")
        prod_name = data.get("prod_name")
        total_amount = data.get("total_amount")
        price = data.get("price")
        quantity = data.get("quantity")
        order_id = get_distributed_id(worker_id=workder_id)
        order_status = 1
        trade_type = "NATIVE"
        prod_cate_id = data.get("prod_cate_id")
        model_name = data.get("model_name", None)
        live_code = data.get("live_code", None)
        # 新增判断来源
        source = request.META.get("HTTP_SOURCE", "pc")
        validate_amount = request.__dict__.get("validate_amount_pass")
        if not validate_amount:
            code = RET.ORDER_AMOUNT_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        save_id = transaction.savepoint()

        unpaid_sql_order = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders (order_id, source, user_id, total_amount, status,prod_cate_id ) "
            f" VALUES ({order_id}, '{source}', {user_id}, {total_amount}, {order_status}, {prod_cate_id})")
        try:
            logger.info(unpaid_sql_order)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_order)
                unpaid_row_count_order = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_orders_items = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders_items (order_id, prod_id, quantity, price, prod_cate_id, model_name, live_code) "
            f" VALUES ({order_id}, {prod_id},{quantity}, {price}, {prod_cate_id}, '{model_name}', '{live_code}')")

        try:
            logger.info(unpaid_sql_orders_items)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_orders_items)
                unpaid_row_orders_items = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_payments = (
            f"INSERT INTO {settings.DEFAULT_DB}.pp_payments (order_id, user_id, amount, status, payment_method, pay_data) "
            f" VALUES ({order_id}, {user_id},{total_amount}, 0, 2, '')")

        try:
            logger.info(unpaid_sql_payments)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_payments)
                unpaid_row_sql_payments = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        if (unpaid_row_count_order +
                unpaid_row_orders_items +
                unpaid_row_sql_payments == 3):

            try:
                data_dict = wxpay(
                    order_id, prod_name, prod_name, total_amount, trade_type
                )  # 调用统一支付接口
                logger.info(data_dict)

            except Exception:
                code = RET.ORDER_CREATE_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)
                raise CstException(code=code, message=message)

            if data_dict.get("return_code") == "SUCCESS":
                # 业务处理

                code_url = data_dict.get("code_url")
                prepay_id = data_dict.get("prepay_id")

                pre_pay_sql_payments = f"""
                            UPDATE {settings.DEFAULT_DB}.pp_payments
                            SET pay_data = %s, pre_pay_id= %s
                            WHERE order_id = %s
                        """

                params = [code_url, prepay_id, order_id]
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(pre_pay_sql_payments, params)
                        pr_pay_row_sql_payments = cursor.rowcount

                        if pr_pay_row_sql_payments > 0:
                            code = RET.OK
                            message = Language.get(code)
                            ret_data = {
                                "pay_url": code_url,
                                "total_amount": total_amount,
                                "order_id": order_id,
                            }
                            transaction.savepoint_commit(save_id)
                            return CstResponse(
                                code=code, message=message, data=[ret_data]
                            )
                        else:
                            code = RET.ALIPAY_PAY_QR_FAIL
                            message = Language.get(code)
                            trace = str(traceback.format_exc())
                            logger.error(trace)
                            raise CstException(code=code, message=message)
                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)
            else:
                code = RET.WECHAT_PAY_QR_FAIL
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)


class FormSheetWechatMiniProgram(APIView):
    @swagger_auto_schema(
        operation_id="9",
        tags=["v3.1"],
        operation_summary="处理微信小程序订单",
        operation_description="This endpoint creates an order based on the given data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "user_id",
                "prod_id",
                "prod_name",
                "total_amount",
                "price",
                "code",
                "quantity",
            ],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "prod_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品ID"
                ),
                "prod_cate_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品cate id。"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商品名称"
                ),
                "total_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="总金额"
                ),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="价格"),
                "open_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="微信用户唯一id"
                ),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品数量"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功状态码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功信息."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="返回的数据",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "req_data": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        description="处理后的支付数据",
                                        properties={
                                            "app_id": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="支付应用ID",
                                            ),
                                            "nonce_str": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="随机字符串",
                                            ),
                                            "package": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="预支付ID",
                                            ),
                                            "sign_type": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="签名类型",
                                            ),
                                            "time_stamp": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="时间戳",
                                            ),
                                            "pay_sign": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="支付签名",
                                            ),
                                        },
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="总金额"
                                    ),
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单ID"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="错误状态码."
                        ),
                        "message": openapi.Schema(
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
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误状态码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息."
                        ),
                    },
                ),
            ),
        },
    )
    @ValidateAmount(param={"db": settings.DEFAULT_DB, "logger": logger})
    @transaction.atomic()
    @ExperienceCardRejectSecPurchase(
        param={"db": settings.DEFAULT_DB, "logger": logger}
    )
    def post(self, request):

        worker_id = 1003
        data = request.data
        user_id = data.get("user_id")

        prod_id = data.get("prod_id")
        prod_cate_id = data.get("prod_cate_id")
        prod_name = data.get("prod_name")
        total_amount = data.get("total_amount")
        price = data.get("price")
        open_id = data.get("open_id")
        quantity = data.get("quantity")
        order_id = get_distributed_id(worker_id=worker_id)
        trade_type = "JSAPI"
        order_status = 1
        model_name = data.get("model_name", None)
        live_code = data.get("live_code", None)
        # 新增判断小程序来源
        source = request.META.get("HTTP_SOURCE", "")

        logger.info(f"current pay from {source}")
        validate_amount = request.__dict__.get("validate_amount_pass")
        #
        if not validate_amount:
            code = RET.ORDER_AMOUNT_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        # get user open_id
        # open_id = get_openid('0b3iZk100D24YP1O7L200PhbSi4iZk1C')
        save_id = transaction.savepoint()

        unpaid_sql_order = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders (order_id, source, user_id, total_amount, status,prod_cate_id ) "
            f" VALUES ({order_id}, '{source}', {user_id}, {total_amount}, {order_status}, {prod_cate_id})")
        try:
            logger.info(unpaid_sql_order)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_order)
                unpaid_row_count_order = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_orders_items = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders_items (order_id, prod_id, quantity, price, prod_cate_id, model_name, live_code) "
            f" VALUES ({order_id}, {prod_id},{quantity}, {price}, {prod_cate_id}, '{model_name}', '{live_code}')")

        try:
            logger.info(unpaid_sql_orders_items)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_orders_items)
                unpaid_row_orders_items = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_payments = (
            f"INSERT INTO {settings.DEFAULT_DB}.pp_payments (order_id, user_id, amount, status, payment_method, pay_data) "
            f" VALUES ({order_id}, {user_id},{total_amount}, 0, 2, '')")

        try:
            logger.info(unpaid_sql_payments)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_payments)
                unpaid_row_sql_payments = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        if (unpaid_row_count_order +
                unpaid_row_orders_items +
                unpaid_row_sql_payments == 3):
            try:

                print(source)
                print("sourcesourcesource")
                if source == "xcx_wcxt":
                    app_id = settings.WC_MINI_PROGRAM_APP_ID
                elif source == "umi_h5":
                    app_id = settings.UMI_MINI_PROGRAM_APP_ID
                elif source == "xcx":
                    print("ddddddddddd")
                    app_id = settings.ZN_MINI_PROGRAM_APP_ID
                    print(app_id)
                else:
                    app_id = settings.MINI_PROGRAM_APP_ID

                data_dict = wxpay(
                    order_id,
                    prod_name,
                    prod_name,
                    total_amount,
                    trade_type,
                    open_id,
                    app_id,
                )  # 调用统一支付接口

            except Exception:
                code = RET.ORDER_CREATE_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)
                raise CstException(code=code, message=message)

            print(data_dict)
            print("data_dictdata_dictdata_dictdata_dict")

            source = request.META.get("HTTP_SOURCE", "")

            if data_dict.get("return_code") == "SUCCESS":
                # 业务处理
                pre_pay_id = data_dict.get("prepay_id")

                processed_ret_pay_data = get_pay_sign(data_dict, source)
                pre_pay_sql_payments = f"""
                                            UPDATE {settings.DEFAULT_DB}.pp_payments
                                            SET pay_data = %s,pre_pay_id=%s
                                            WHERE order_id = %s
                                        """

                params = [
                    json.dumps(processed_ret_pay_data, ensure_ascii=False),
                    pre_pay_id,
                    order_id,
                ]
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(pre_pay_sql_payments, params)
                        pr_pay_row_sql_payments = cursor.rowcount

                        if pr_pay_row_sql_payments > 0:
                            code = RET.OK
                            message = Language.get(code)
                            ret_data = {
                                "req_data": processed_ret_pay_data,
                                "total_amount": total_amount,
                                "order_id": order_id,
                            }
                            transaction.savepoint_commit(save_id)
                            return CstResponse(
                                code=code, message=message, data=[ret_data]
                            )
                        else:
                            code = RET.ALIPAY_PAY_QR_FAIL
                            message = Language.get(code)
                            trace = str(traceback.format_exc())
                            logger.error(trace)
                            raise CstException(code=code, message=message)
                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

            else:
                code = RET.WECHAT_PAY_QR_FAIL
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)
        else:
            code = RET.WECHAT_PAY_QR_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class FormSheetWechatH5(APIView):
    @swagger_auto_schema(
        operation_id="111",
        tags=["v3.1"],
        operation_summary="处理微信H5订单",
        operation_description="This endpoint creates an order based on the given data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "user_id",
                "prod_id",
                "prod_name",
                "total_amount",
                "price",
                "code",
                "quantity",
            ],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "prod_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品ID"
                ),
                "prod_cate_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品cate id。"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="商品名称"
                ),
                "total_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="总金额"
                ),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="价格"),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="商品数量"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功状态码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功信息."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="返回的数据",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "req_data": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        description="处理后的支付数据",
                                        properties={
                                            "app_id": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="支付应用ID",
                                            ),
                                            "nonce_str": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="随机字符串",
                                            ),
                                            "package": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="预支付ID",
                                            ),
                                            "sign_type": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="签名类型",
                                            ),
                                            "time_stamp": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="时间戳",
                                            ),
                                            "pay_sign": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="支付签名",
                                            ),
                                        },
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="总金额"
                                    ),
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单ID"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="错误状态码."
                        ),
                        "message": openapi.Schema(
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
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误状态码."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误信息."
                        ),
                    },
                ),
            ),
        },
    )
    @ValidateAmount(param={"db": settings.DEFAULT_DB, "logger": logger})
    @transaction.atomic()
    @ExperienceCardRejectSecPurchase(
        param={"db": settings.DEFAULT_DB, "logger": logger}
    )
    def post(self, request):

        worker_id = 1003
        data = request.data
        user_id = data.get("user_id")

        prod_id = data.get("prod_id")
        prod_cate_id = data.get("prod_cate_id")
        prod_name = data.get("prod_name")
        total_amount = data.get("total_amount")
        price = data.get("price")
        quantity = data.get("quantity")
        order_id = get_distributed_id(worker_id=worker_id)
        trade_type = "MWEB"
        model_name = data.get("model_name", None)
        live_code = data.get("live_code", None)
        order_status = 1
        # 新增判断小程序来源
        source = request.META.get("HTTP_SOURCE", "")
        validate_amount = request.__dict__.get("validate_amount_pass")

        if not validate_amount:
            code = RET.ORDER_AMOUNT_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        save_id = transaction.savepoint()

        unpaid_sql_order = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders (order_id, source, user_id, total_amount, status,prod_cate_id ) "
            f" VALUES ({order_id}, '{source}', {user_id}, {total_amount}, {order_status}, {prod_cate_id})")
        try:
            logger.info(unpaid_sql_order)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_order)
                unpaid_row_count_order = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_orders_items = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders_items (order_id, prod_id, quantity, price, prod_cate_id, model_name, live_code) "
            f" VALUES ({order_id}, {prod_id},{quantity}, {price}, {prod_cate_id}, '{model_name}', '{live_code}')")

        try:
            logger.info(unpaid_sql_orders_items)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_orders_items)
                unpaid_row_orders_items = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_payments = (
            f"INSERT INTO {settings.DEFAULT_DB}.pp_payments (order_id, user_id, amount, status, payment_method, pay_data) "
            f" VALUES ({order_id}, {user_id},{total_amount}, 0, 2, '')")

        try:
            logger.info(unpaid_sql_payments)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_payments)
                unpaid_row_sql_payments = cursor.rowcount
        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        if (unpaid_row_count_order +
                unpaid_row_orders_items +
                unpaid_row_sql_payments == 3):
            try:

                app_id = settings.APP_ID

                if request.META.get("HTTP_X_FORWARDED_FOR"):
                    spbill_create_ip = request.META["HTTP_X_FORWARDED_FOR"]
                else:
                    spbill_create_ip = request.META["REMOTE_ADDR"]

                print(spbill_create_ip)
                print(
                    "spbill_create_ipspbill_create_ipspbill_create_ipspbill_create_ipspbill_create_ipspbill_create_ip"
                )
                data_dict = wxpay(
                    order_id,
                    prod_name,
                    prod_name,
                    total_amount,
                    trade_type,
                    spbill_create_ip,
                    app_id,
                )  # 调用统一支付接口

            except Exception:
                code = RET.ORDER_CREATE_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)
                raise CstException(code=code, message=message)

            source = request.META.get("HTTP_SOURCE", "")

            if data_dict.get("return_code") == "SUCCESS":
                # 业务处理
                pre_pay_id = data_dict.get("prepay_id")

                processed_ret_pay_data = get_pay_sign(data_dict, source)
                pre_pay_sql_payments = f"""
                                            UPDATE {settings.DEFAULT_DB}.pp_payments
                                            SET pay_data = %s,pre_pay_id=%s
                                            WHERE order_id = %s
                                        """

                params = [
                    json.dumps(processed_ret_pay_data, ensure_ascii=False),
                    pre_pay_id,
                    order_id,
                ]
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(pre_pay_sql_payments, params)
                        pr_pay_row_sql_payments = cursor.rowcount

                        if pr_pay_row_sql_payments > 0:
                            code = RET.OK
                            message = Language.get(code)
                            ret_data = {
                                "req_data": processed_ret_pay_data,
                                "total_amount": total_amount,
                                "order_id": order_id,
                            }
                            transaction.savepoint_commit(save_id)
                            return CstResponse(
                                code=code, message=message, data=[ret_data]
                            )
                        else:
                            code = RET.ALIPAY_PAY_QR_FAIL
                            message = Language.get(code)
                            trace = str(traceback.format_exc())
                            logger.error(trace)
                            raise CstException(code=code, message=message)
                except Exception:
                    code = RET.WECHAT_PAY_QR_FAIL
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

            else:
                code = RET.WECHAT_PAY_QR_FAIL
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)
        else:
            code = RET.WECHAT_PAY_QR_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


# 旧版， 暂时废弃
# class UpdateOrderWechat(APIView):
#
#     @swagger_auto_schema(
#         operation_id='11',
#         tags=['v3.1'],
#         operation_summary='更新订单微信回调',
#         operation_description='处理支付成功逻辑，根据订单号修改后台数据库状态。',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'xml_data': openapi.Schema(
#                     type=openapi.TYPE_STRING,
#                     description='XML格式的回调数据'
#                 )
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='回调成功',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'return_code': openapi.Schema(
#                             type=openapi.TYPE_STRING,
#                             description='回调返回代码'
#                         ),
#                         'return_msg': openapi.Schema(
#                             type=openapi.TYPE_STRING,
#                             description='回调返回消息'
#                         )
#                     }
#                 )
#             ),
#             status.HTTP_400_BAD_REQUEST: openapi.Response(
#                 description='错误的请求',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(
#                             type=openapi.TYPE_INTEGER,
#                             description='错误代码'
#                         ),
#                         'message': openapi.Schema(
#                             type=openapi.TYPE_STRING,
#                             description='错误消息'
#                         )
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='内部服务器错误',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(
#                             type=openapi.TYPE_INTEGER,
#                             description='错误代码'
#                         ),
#                         'message': openapi.Schema(
#                             type=openapi.TYPE_STRING,
#                             description='错误消息'
#                         )
#                     }
#                 )
#             )
#         }
#     )
#     @transaction.atomic()
#     def post(self, request):
#
#         data_dict = trans_xml_to_dict(request.body)  # 回调数据转字典
#         logger.info('支付回调结果', data_dict)
#         sign = data_dict.pop('sign')  # 取出签名
#
#         try:
#             back_sign = get_sign(data_dict, settings.API_KEY)  # 计算签名
#
#         except Exception:
#             code = RET.ALIPAY_PAY_CALLBACK_FAIL
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)
#         save_id = transaction.savepoint()
#         # 验证签名是否与回调签名相同
#         if sign == back_sign and data_dict['return_code'] == 'SUCCESS':
#             # 处理支付成功逻辑，根据订单号修改后台数据库状态
#             # 返回接收结果给微信，否则微信会每隔8分钟发送post请求
#
#             order_id = data_dict.get('out_trade_no')
#             trade_id = data_dict.get('transaction_id')
#
#             update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {trade_id} WHERE order_id = {order_id}"
#             update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1  WHERE order_id = {order_id}"
#
#             try:
#                 with connection.cursor() as cursor:
#                     cursor.execute(update_payment)
#                     update_payment_rowcount = cursor.rowcount
#
#                 with connection.cursor() as cursor:
#                     cursor.execute(update_order)
#                     update_order_rowcount = cursor.rowcount
#                 if update_order_rowcount + update_payment_rowcount == 2:
#
#                     # 查询用户购买的产品类别
#                     sql_get_prod_cate = f"SELECT a.user_id, a.prod_cate_id, b.prod_id,b.price, b.quantity,a.total_amount FROM {settings.DEFAULT_DB}.po_orders a " \
#                                         f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id " \
#                                         f" WHERE  a.order_id = {order_id}"
#
#                     logger.info(sql_get_prod_cate)
#
#                     try:
#                         with connection.cursor() as cursor:
#                             cursor.execute(sql_get_prod_cate)
#                             prod_cate_data = MysqlOper.get_query_result(cursor)
#
#                             if prod_cate_data:
#                                 user_id = prod_cate_data[0].get('user_id')
#                                 prod_id = prod_cate_data[0].get('prod_id')
#                                 prod_cate_id = prod_cate_data[0].get('prod_cate_id')
#                                 quantity = prod_cate_data[0].get('quantity')
#                                 price = prod_cate_data[0].get('price')
#                                 total_amount = prod_cate_data[0].get('total_amount')
#                             else:
#                                 code = RET.DB_ERR
#                                 message = Language.get(code)
#                                 trace = str(traceback.format_exc())
#                                 logger.error(trace)
#                                 transaction.savepoint_rollback(save_id)
#                                 raise CstException(code=code, message=message)
#                     except Exception:
#                         code = RET.DB_ERR
#                         message = Language.get(code)
#                         trace = str(traceback.format_exc())
#                         logger.error(trace)
#                         transaction.savepoint_rollback(save_id)
#                         raise CstException(code=code, message=message)
#
#                     config_prod_redis = get_redis_connection('config')
#                     cates_dict = config_prod_redis.get('config:products:cate')
#                     cates_dict = json.loads(cates_dict)
#                     current_cate = cates_dict.get(prod_cate_id)
#
#                     if current_cate == "member":
#                         insert_extend = gadgets.insert_new_member(order_id=order_id, conn=connection, pay=True)
#                     elif current_cate == "package":
#                         insert_extend = gadgets.insert_data_plus(user_id=user_id, prod_id=prod_id, order_id=order_id,
#                                                                  quantity=quantity, price=price)
#                     elif current_cate == "universal":
#                         insert_extend = gadgets.insert_data_plus(user_id=user_id, prod_id=prod_id, order_id=order_id,
#                                                                  quantity=quantity, price=price)
#                     elif current_cate == "reseller":
#                         insert_extend = True
#                     else:
#                         # TODO 分销体系逻辑
#                         insert_extend = ''
#                     # 分销逻辑
#                     if int(prod_cate_id) == 4:
#                         response_upgrade_level = gadgets.extend_upgrade_distribution_level(user_id)
#                         response_pay_commission = gadgets.extend_pay_commission(user_id, order_id, total_amount, '1')
#
#                         if response_upgrade_level and response_pay_commission:
#                             call_distribution = True
#                         else:
#                             call_distribution = False
#                         call_out_video = True
#                         call_clone = True
#                         call_submit_voice = True
#
#                     else:
#                         if int(prod_cate_id) in [7, 8]:
#                             call_distribution = True
#                             insert_extend = True
#                             call_out_video = gadgets.update_out_video_status(order_id)
#                             call_clone = gadgets.update_clone_status(order_id)
#                             call_submit_voice = gadgets.submit_customized_voice(order_id)
#                         else:
#                             response_pay_commission = gadgets.extend_pay_commission(user_id, order_id, total_amount,
#                                                                                     '0')
#                             if response_pay_commission:
#                                 call_distribution = True
#                             else:
#                                 call_distribution = False
#
#                             call_submit_voice = True
#                             call_out_video = True
#                             call_clone = True
#                     print(insert_extend)
#                     print(call_distribution)
#                     print(call_submit_voice)
#                     print(call_out_video)
#                     print(call_clone)
#                     print('fffffffff')
#                     if insert_extend and call_distribution and call_out_video and call_clone and call_submit_voice:
#                         transaction.savepoint_commit(save_id)
#                         return HttpResponse(trans_dict_to_xml({'return_code': 'SUCCESS', 'return_msg': 'OK'}))
#                     else:
#                         code = RET.DB_ERR
#                         message = Language.get(code)
#                         trace = str(traceback.format_exc())
#                         logger.error(trace)
#                         transaction.savepoint_rollback(save_id)
#
#                         raise CstException(code=code, message=message)
#                 else:
#                     transaction.savepoint_rollback(save_id)
#                     return HttpResponse(trans_dict_to_xml({'return_code': 'FAIL', 'return_msg': 'SIGNERROR'}))
#             except Exception:
#                 trace = str(traceback.format_exc())
#                 logger.error(trace)
#                 transaction.savepoint_rollback(save_id)
#
#                 return HttpResponse(trans_dict_to_xml({'return_code': 'FAIL', 'return_msg': 'SIGNERROR'}))
#         else:
#
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             transaction.savepoint_rollback(save_id)
#
# return HttpResponse(trans_dict_to_xml({'return_code': 'FAIL',
# 'return_msg': 'SIGNERROR'}))


class UpdateOrderWechat(APIView):
    @swagger_auto_schema(
        operation_id="11",
        tags=["v3.1"],
        operation_summary="更新订单微信回调",
        operation_description="处理支付成功逻辑，根据订单号修改后台数据库状态。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "xml_data": openapi.Schema(
                    type=openapi.TYPE_STRING, description="XML格式的回调数据"
                )
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="回调成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "return_code": openapi.Schema(
                            type=openapi.TYPE_STRING, description="回调返回代码"
                        ),
                        "return_msg": openapi.Schema(
                            type=openapi.TYPE_STRING, description="回调返回消息"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误的请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    def post(self, request):

        data_dict = trans_xml_to_dict(request.body)  # 回调数据转字典
        logger.info("支付回调结果", data_dict)
        sign = data_dict.pop("sign")  # 取出签名

        print('2222222222')
        try:
            back_sign = get_sign(data_dict, settings.API_KEY)  # 计算签名

        except Exception:
            code = RET.ALIPAY_PAY_CALLBACK_FAIL
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)
        print(333333)
        save_id = transaction.savepoint()
        # 验证签名是否与回调签名相同
        if sign == back_sign and data_dict["return_code"] == "SUCCESS":
            # 处理支付成功逻辑，根据订单号修改后台数据库状态
            # 返回接收结果给微信，否则微信会每隔8分钟发送post请求

            order_id = data_dict.get("out_trade_no")
            trade_id = data_dict.get("transaction_id")

            update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {trade_id} WHERE order_id = {order_id}"
            update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1  WHERE order_id = {order_id}"

            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_payment)
                    update_payment_rowcount = cursor.rowcount

                with connection.cursor() as cursor:
                    cursor.execute(update_order)
                    update_order_rowcount = cursor.rowcount
                if update_order_rowcount + update_payment_rowcount == 2:

                    # 查询用户购买的产品类别
                    sql_get_prod_cate = (
                        f"SELECT a.user_id, a.prod_cate_id, b.prod_id,b.price, b.quantity,a.total_amount FROM {settings.DEFAULT_DB}.po_orders a "
                        f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id "
                        f" WHERE  a.order_id = {order_id}")

                    logger.info(sql_get_prod_cate)

                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_get_prod_cate)
                            prod_cate_data = MysqlOper.get_query_result(cursor)

                            if prod_cate_data:
                                user_id = prod_cate_data[0].get("user_id")
                                prod_id = prod_cate_data[0].get("prod_id")
                                prod_cate_id = prod_cate_data[0].get(
                                    "prod_cate_id")
                                quantity = prod_cate_data[0].get("quantity")
                                price = prod_cate_data[0].get("price")
                                total_amount = prod_cate_data[0].get(
                                    "total_amount")
                            else:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                transaction.savepoint_rollback(save_id)
                                raise CstException(code=code, message=message)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        raise CstException(code=code, message=message)

                    user_active_data = {"user_id": user_id}

                    req_url_active = (
                            settings.SERVER_BILL_URL
                            + ":"
                            + settings.SERVER_BILL_PORT
                            + settings.IS_ACTIVE_ADDRESS
                    )
                    user_active_req = requests.post(
                        url=req_url_active, data=user_active_data
                    )

                    if user_active_req.status_code == 200:
                        user_active_req_data = json.loads(user_active_req.text)
                        if user_active_req_data.get("code") == 20000:
                            user_is_active = user_active_req_data.get("data")
                        else:
                            user_is_active = False
                    else:
                        user_is_active = False

                    print(user_is_active)
                    print("user_is_activeuser_is_activeuser_is_activeuser_is_active")
                    if user_is_active:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_RENEW
                        )
                    else:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_ADDRESS
                        )

                    insert_member_success = False
                    insert_package_success = False
                    call_distribution = False
                    call_submit_voice = False
                    call_out_video = False
                    call_clone = False
                    call_huoshan_sound = False
                    # 会员类别，写入会员有效期等数据和写入算力值&算力值有效期
                    if int(prod_cate_id) == 3:
                        insert_member_config = gadgets.insert_new_member(
                            order_id=order_id, conn=connection, pay=True
                        )

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": prod_id,
                            "quantity": quantity,
                            "prod_cate_id": prod_cate_id,
                        }
                        insert_member_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        if insert_member_hashrate_req.status_code == 200:

                            insert_member_hashrate_data = json.loads(
                                insert_member_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                print(insert_member_hashrate_data)
                                print(
                                    "insert_member_hashrate_datainsert_member_hashrate_data"
                                )
                                insert_member_hashrate = True
                            else:
                                insert_member_hashrate = False
                        else:
                            insert_member_hashrate = False

                        if insert_member_config and insert_member_hashrate:
                            insert_member_success = True
                            insert_package_success = True
                        else:
                            insert_member_success = False
                            insert_package_success = False

                    # 流量包写入算力值和算力值有效期
                    elif int(prod_cate_id) == 6:

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": prod_id,
                            "quantity": quantity,
                            "prod_cate_id": prod_cate_id,
                        }
                        insert_package_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        if insert_package_hashrate_req.status_code == 200:
                            insert_member_hashrate_data = json.loads(
                                insert_package_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                insert_package_success = True
                                insert_member_success = True
                    else:
                        # 非会员和流量包外的其他逻辑
                        insert_member_success = True
                        insert_package_success = True

                    print(44444444444)
                    # 分销逻辑
                    if int(prod_cate_id) == 4:
                        response_upgrade_level = (
                            gadgets.extend_upgrade_distribution_level(user_id)
                        )
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "1")

                        if response_upgrade_level and response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False
                        insert_member_success = True
                        insert_package_success = True
                        call_out_video = True
                        call_clone = True
                        call_submit_voice = True


                    elif int(prod_cate_id) in [7, 8, 9]:
                        print(555555555)
                        if int(prod_cate_id) in [7, 8]:

                            call_distribution = True

                            # insert_member_success = True

                            # insert_package_success = True

                            call_out_video = gadgets.update_out_video_status(

                                order_id)

                            call_clone = gadgets.update_clone_status(order_id)

                            call_submit_voice = gadgets.submit_customized_voice(

                                order_id)

                            call_huoshan_sound = True

                        elif int(prod_cate_id) == 9:
                            print(666666)
                            call_huoshan_sound_req = gadgets.call_huoshan_sound_clone(order_id)

                            if call_huoshan_sound_req:

                                call_huoshan_sound = True

                                call_submit_voice = True

                                call_out_video = True

                                call_clone = True

                                call_distribution = True

                            else:

                                call_huoshan_sound = False

                                call_submit_voice = True

                                call_out_video = True

                                call_clone = True

                                call_distribution = True


                        else:

                            response_pay_commission = gadgets.extend_pay_commission(

                                user_id, order_id, total_amount, "0")

                            if response_pay_commission:

                                call_distribution = True

                            else:

                                call_distribution = False

                            call_submit_voice = True

                            call_out_video = True

                            call_clone = True

                            call_huoshan_sound = True

                    print("insert_package_success: ", insert_package_success)

                    print("insert_member_success: ", insert_member_success)

                    print("call_distribution:", call_distribution)

                    print("call_submit_voice:", call_submit_voice)

                    print("call_out_video:", call_out_video)

                    print("call_clone:", call_clone)

                    print("call_huoshan_sound:", call_huoshan_sound)

                    if (

                            insert_package_success

                            and insert_member_success

                            and call_distribution

                            and call_out_video

                            and call_clone

                            and call_submit_voice

                            and call_huoshan_sound

                    ):
                        transaction.savepoint_commit(save_id)
                        return HttpResponse(
                            trans_dict_to_xml(
                                {"return_code": "SUCCESS", "return_msg": "OK"}
                            )
                        )
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)

                        raise CstException(code=code, message=message)
                else:
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(
                        trans_dict_to_xml(
                            {"return_code": "FAIL", "return_msg": "SIGNERROR"}
                        )
                    )
            except Exception:
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)

                return HttpResponse(
                    trans_dict_to_xml(
                        {"return_code": "FAIL", "return_msg": "SIGNERROR"}
                    )
                )
        else:

            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)

            return HttpResponse(trans_dict_to_xml(
                {"return_code": "FAIL", "return_msg": "SIGNERROR"}))


class QueryStatusWechat(APIView):
    @swagger_auto_schema(
        operation_id="11",
        tags=["v3.1"],
        operation_summary="更新订单微信回调",
        operation_description="处理支付成功逻辑，根据订单号修改后台数据库状态。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "xml_data": openapi.Schema(
                    type=openapi.TYPE_STRING, description="XML格式的回调数据"
                )
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="回调成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "return_code": openapi.Schema(
                            type=openapi.TYPE_STRING, description="回调返回代码"
                        ),
                        "return_msg": openapi.Schema(
                            type=openapi.TYPE_STRING, description="回调返回消息"
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误的请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    def post(self, request):

        order_id = request.data.get("order_id")
        soure = request.data.get("source")
        pay_result = query_payment_status(order_id, source=soure)

        save_id = transaction.savepoint()
        # 验证签名是否与回调签名相同
        if pay_result:
            # 处理支付成功逻辑，根据订单号修改后台数据库状态
            # 返回接收结果给微信，否则微信会每隔8分钟发送post请求

            order_id = pay_result.get("out_trade_no")
            trade_id = pay_result.get("transaction_id")

            update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {trade_id} WHERE order_id = {order_id}"
            update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1  WHERE order_id = {order_id}"

            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_payment)
                    update_payment_rowcount = cursor.rowcount

                with connection.cursor() as cursor:
                    cursor.execute(update_order)
                    update_order_rowcount = cursor.rowcount
                if update_order_rowcount + update_payment_rowcount == 2:

                    # 查询用户购买的产品类别
                    sql_get_prod_cate = (
                        f"SELECT a.user_id, a.prod_cate_id, b.prod_id,b.price, b.quantity,a.total_amount FROM {settings.DEFAULT_DB}.po_orders a "
                        f"LEFT JOIN {settings.DEFAULT_DB}.po_orders_items b ON a.order_id = b.order_id "
                        f" WHERE  a.order_id = {order_id}")

                    logger.info(sql_get_prod_cate)

                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_get_prod_cate)
                            prod_cate_data = MysqlOper.get_query_result(cursor)

                            if prod_cate_data:
                                user_id = prod_cate_data[0].get("user_id")
                                prod_id = prod_cate_data[0].get("prod_id")
                                prod_cate_id = prod_cate_data[0].get(
                                    "prod_cate_id")
                                quantity = prod_cate_data[0].get("quantity")
                                price = prod_cate_data[0].get("price")
                                total_amount = prod_cate_data[0].get(
                                    "total_amount")
                            else:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                transaction.savepoint_rollback(save_id)
                                raise CstException(code=code, message=message)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        raise CstException(code=code, message=message)

                    config_prod_redis = get_redis_connection("config")
                    cates_dict = config_prod_redis.get("config:products:cate")
                    cates_dict = json.loads(cates_dict)
                    current_cate = cates_dict.get(prod_cate_id)

                    if current_cate == "member":
                        insert_extend = gadgets.insert_new_member(
                            order_id=order_id, conn=connection, pay=True
                        )
                    elif current_cate == "package":
                        insert_extend = gadgets.insert_data_plus(
                            user_id=user_id,
                            prod_id=prod_id,
                            order_id=order_id,
                            quantity=quantity,
                            price=price,
                        )
                    elif current_cate == "universal":
                        insert_extend = gadgets.insert_data_plus(
                            user_id=user_id,
                            prod_id=prod_id,
                            order_id=order_id,
                            quantity=quantity,
                            price=price,
                        )
                    elif current_cate == "reseller":
                        insert_extend = True
                    else:
                        # TODO 分销体系逻辑
                        insert_extend = ""
                    print("zzzzzzzzzzzzzzzzzzzzzzz")
                    # 分销逻辑
                    if int(prod_cate_id) == 4:
                        print("kkkkkkkkkkkkk")
                        response_upgrade_level = (
                            gadgets.extend_upgrade_distribution_level(user_id)
                        )
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "1")

                        if response_upgrade_level and response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False

                    else:
                        response_pay_commission = gadgets.extend_pay_commission(
                            user_id, order_id, total_amount, "0")
                        if response_pay_commission:
                            call_distribution = True
                        else:
                            call_distribution = False

                    if insert_extend and call_distribution:
                        transaction.savepoint_commit(save_id)
                        return HttpResponse(
                            trans_dict_to_xml(
                                {"return_code": "SUCCESS", "return_msg": "OK"}
                            )
                        )
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)

                        raise CstException(code=code, message=message)
                else:
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(
                        trans_dict_to_xml(
                            {"return_code": "FAIL", "return_msg": "SIGNERROR"}
                        )
                    )
            except Exception:
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)

                return HttpResponse(
                    trans_dict_to_xml(
                        {"return_code": "FAIL", "return_msg": "SIGNERROR"}
                    )
                )
        else:

            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)

            return HttpResponse(trans_dict_to_xml(
                {"return_code": "FAIL", "return_msg": "SIGNERROR"}))


class PayResult(APIView):
    @swagger_auto_schema(
        operation_id="12",
        tags=["支付结果查询"],
        operation_summary="支付结果查询",
        operation_description="该接口用于查询支付结果。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "order_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="订单ID"
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
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="订单详情列表",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="订单ID"
                                    ),
                                    "payment_method": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="支付方式"
                                    ),
                                    "pay_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="支付ID"
                                    ),
                                    "prod_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="商品ID"
                                    ),
                                    "prod_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="商品名称"
                                    ),
                                    "status": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="订单状态"
                                    ),
                                    "amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="支付金额"
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单创建时间"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="请求错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data
        order_id = data.get("order_id")
        # Query only the 'status' field for the first time to reduce server
        # load
        sql_fetch_status = f"SELECT status FROM {settings.DEFAULT_DB}.pp_payments WHERE order_id = {order_id}"
        status = 0
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_status)
                data = MysqlOper.get_query_result(cursor)
                if data:
                    status = data[0].get("status")
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        if int(status) == 1:
            # Upon confirming a successful payment, retrieve all fields
            sql_fetch_order_details = f"""
            SELECT pp_payments.status, pp_payments.payment_method,pp_payments.created_at,
            pp_payments.amount, pp_payments.pay_id, pp_payments.order_id,
             pp_payments.created_at, po_orders_items.prod_id, pp_products.prod_name
            FROM po_orders_items
            INNER JOIN pp_products ON po_orders_items.prod_id = pp_products.prod_id
            INNER JOIN pp_payments ON po_orders_items.order_id = pp_payments.order_id
            WHERE po_orders_items.order_id = '{order_id}';
            """

            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_fetch_order_details)
                    data = MysqlOper.get_query_result(cursor)
                    if data:
                        data = data[0]
                        status = data.get("status")
                        payment_method = data.get("payment_method")
                        pay_id = data.get("pay_id")
                        order_id = data.get("order_id")
                        prod_id = data.get("prod_id")
                        prod_name = data.get("prod_name")
                        amount = data.get("amount")
                        created_at = data.get("created_at")

                        code = RET.OK
                        message = Language.get(code)
                        ret_data = {
                            "order_id": order_id,
                            "payment_method": payment_method,
                            "pay_id": pay_id,
                            "prod_id": prod_id,
                            "prod_name": prod_name,
                            "status": status,
                            "amount": amount,
                            "created_at": created_at,
                        }
                        return CstResponse(
                            code=code, message=message, data=[ret_data])
            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)

        else:
            if int(status) == 0:
                code = RET.OK
                message = Language.get(code)
                ret_data = {"order_id": order_id, "status": status}
                return CstResponse(code=code, message=message, data=[ret_data])

            code = RET.PAY_RES_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)

            raise CstException(code=code, message=message)


class Tokens(APIView):
    # def get(self, request):
    #
    #     return CstResponse(code=1, message=1, data=1)

    """
    Tokens视图

    get: 获取token信息
    post: 更新token信息
    put: 减少token数量
    """

    @swagger_auto_schema(
        operation_id="13",
        tags=["用户token【废弃】"],
        operation_summary="获取token信息",
        operation_description="获取用户的token数量及购买上限",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户id"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="请求成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="请求成功信息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="用户的token数量及购买上限",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "tokens": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="用户token数量",
                                    ),
                                    "count": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="用户购买上限"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="请求失败代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="请求失败信息"
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
                            type=openapi.TYPE_INTEGER, description="请求失败代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="请求失败信息"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")

        sql_fetch_tokens = f"SELECT tokens, count FROM {settings.DEFAULT_DB}.os_statistics  WHERE user_id = {user_id} AND is_delete = 0"

        logger.info(sql_fetch_tokens)
        list_data: List[defaultdict] = []

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_tokens)
                query_data = MysqlOper.get_query_result(cursor)
                for each_user in query_data:
                    prod_data = defaultdict(dict)
                    tokens = each_user.get("tokens")
                    limit = each_user.get("count")
                    prod_data["tokens"] = tokens if int(tokens) > 0 else 0
                    prod_data["count"] = limit if int(limit) > 0 else 0
                    list_data.append(prod_data)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=list_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="14",
        tags=["用户token【废弃】"],
        operation_summary="减少用户令牌数量",
        operation_description="该方法通过指定的数量减少数据库中用户的令牌数量。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "count_operate_num"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="要减少令牌数量的用户的ID。"
                ),
                "count_operate_num": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="要减少用户令牌数量的数量。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="令牌信息列表。",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "count": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="更新后的令牌数量。",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    def put(self, request):

        data = request.data
        user_id = data.get("user_id")
        count_operate_num = data.get("count_operate_num")

        save_id = transaction.savepoint()
        sql_update_num = (
            f"UPDATE {settings.DEFAULT_DB}.`os_statistics` SET `count` = `count` - {count_operate_num}"
            f" WHERE `user_id` = {user_id}")
        logger.info(sql_update_num)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update_num)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    list_data = []
                    sql_fetch_num = f"SELECT count FROM {settings.DEFAULT_DB}.os_statistics WHERE user_id = {user_id} AND is_delete = 0 "
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_fetch_num)
                            query_data = MysqlOper.get_query_result(cursor)
                            for each in query_data:
                                prod_data = defaultdict(dict)
                                count = each.get("count")
                                prod_data["count"] = count if int(
                                    count) > 0 else 0
                                list_data.append(prod_data)
                        code = RET.OK
                        message = Language.get(code)
                        transaction.savepoint_commit(save_id)
                        return CstResponse(
                            code=code, message=message, data=list_data)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        raise CstException(code=code, message=message)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="15",
        tags=["用户token【废弃】"],
        operation_summary="用户注册后清空token和count",
        operation_description="用户注册后清空token和count。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="需要清空的用户id。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="已删除的订单信息列表。",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="已经清空token和count的用户id。",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="服务器内部错误",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def delete(self, request):

        data = request.data
        user_id = data.get("user_id")

        sql_update_zero = (
            f"UPDATE {settings.DEFAULT_DB}.`os_statistics` SET `count` = 0, tokens = 0 "
            f" WHERE `user_id` = {user_id}")
        logger.info(sql_update_zero)
        list_data = []

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update_zero)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    ret_data = {"user_id": user_id}
                    list_data.append(ret_data)
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(
                        code=code, message=message, data=list_data)
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class BusinessCooperation(APIView):
    @swagger_auto_schema(
        operation_id="16",
        tags=["业务合作【新】"],
        operation_summary="业务合作",
        operation_description="This endpoint allows users to submit their business cooperation details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "phone", "details"],
            properties={
                "type": openapi.Schema(type=openapi.TYPE_STRING, description="合作类型."),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="合作名称."),
                "phone": openapi.Schema(type=openapi.TYPE_STRING, description="联系电话."),
                "details": openapi.Schema(
                    type=openapi.TYPE_STRING, description="合作详情."
                ),
                "position": openapi.Schema(type=openapi.TYPE_STRING, description="职位."),
                "company": openapi.Schema(
                    type=openapi.TYPE_STRING, description="公司名称."
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID."
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of submitted cooperation details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="合作名称."
                                    ),
                                    "phone": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="联系电话."
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data
        type = data.get("type")
        name = data.get("name")
        user_id = data.get("user_id")
        phone = data.get("phone")
        company = data.get("company")
        position = data.get("position")
        details = data.get("details")

        if int(type) == 20:
            details = "申请运营商，特定人员处理"

        sql_business_cooperation = (
            f"INSERT INTO {settings.DEFAULT_DB}.ob_business_cooperation (type, name,user_id,  phone, company,position, cooperation_details)"
            " VALUES ( %s, %s, %s, %s,%s, %s, %s)")

        sql_values = (type, name, user_id, phone, company, position, details)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_business_cooperation, sql_values)

                rowcount = cursor.rowcount
                logger.info(cursor._executed)
                if rowcount == 1:
                    code = RET.OK
                    message = Language.get(code)
                    ret_data = {"name": name, "phone": phone}
                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    error = str(traceback.format_exc())
                    logger.error(error)
                    raise CstException(code=code, message=message)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class RePay(APIView):
    @swagger_auto_schema(
        operation_id="17",
        tags=["v3.1"],
        operation_summary="重新支付订单",
        operation_description="This endpoint allows users to re-pay for an order.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_id", "user_id"],
            properties={
                "order_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The ID of the order."
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The ID of current user."
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="Details of the re-paid order.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="The ID of the order.",
                                    ),
                                    "pay_data": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="The payment data of the order.",
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER,
                            description="30011 Order expired.",
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="订单过期"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="Details of the order expired data",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "order_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="The ID of the order.",
                                    ),
                                    "pay_data": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description='The payment data of the order. "" if orde rexpired  ',
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    @csrf_exempt
    @transaction.atomic()
    def post(self, request):
        order_id = request.data.get("order_id")
        user_id = request.data.get("user_id")
        current_time = int(datetime.datetime.now().timestamp())

        save_id = transaction.savepoint()

        # 查询订单
        sql_query_order = (
            f"SELECT user_id, pay_data, UNIX_TIMESTAMP(created_at) AS created_at FROM {settings.DEFAULT_DB}.pp_payments "
            f"WHERE order_id = '{order_id}' AND is_delete = 0")
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query_order)
                result = MysqlOper.get_query_result(cursor)

                if result:
                    db_user_id = result[0]["user_id"]

                    if db_user_id != user_id:
                        code = RET.NOT_YOUR_ORDER
                        message = Language.get(code)
                        return CstResponse(code=code, message=message, data=[])

                    pay_data = result[0]["pay_data"]
                    created_at = result[0]["created_at"]
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    logger.error(f"Order {order_id} not found")
                    raise CstException(code=code, message=message)
        except Exception as e:
            code = RET.DB_ERR
            message = Language.get(code)
            logger.error(f"Failed to query order: {e}")
            raise CstException(code=code, message=message)

        if (current_time - int(created_at)) > 900:
            update_payments_status = f"UPDATE pp_payments SET status = 4 WHERE order_id = '{order_id}' AND is_delete = 0"
            update_order_status = f"UPDATE po_orders SET status = 4 WHERE order_id = '{order_id}' AND is_delete = 0"
            logger.error(update_payments_status)
            logger.error(update_order_status)
            try:
                with connection.cursor() as cursor:
                    cursor.execute(update_payments_status)
                    rowcount_payments = cursor.rowcount
                with connection.cursor() as cursor:
                    cursor.execute(update_order_status)
                    rowcount_order = cursor.rowcount

                if rowcount_payments + rowcount_order == 2:

                    code = RET.ORDER_EXPIRED
                    message = Language.get(code)
                    ret_data = {"order_id": order_id, "pay_data": ""}
                    transaction.savepoint_commit(save_id)
                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    logger.info(f"Order {order_id} status set to invalid")
                    transaction.savepoint_rollback(save_id)
                    return CstResponse(code=code, message=message)
            except Exception as e:
                code = RET.DB_ERR
                message = Language.get(code)
                logger.error(f"Failed to update order status: {e}")
                transaction.savepoint_rollback(save_id)
                raise CstException(code=code, message=message)
        else:
            code = RET.OK
            message = Language.get(code)
            data = {"order_id": order_id, "pay_data": pay_data}
            transaction.savepoint_commit(save_id)
            return CstResponse(code=code, message=message, data=[data])


class UserCountInit(APIView):
    @swagger_auto_schema(
        operation_id="18",
        tags=["用户次数初始化【废弃】"],
        operation_summary="用户次数初始化",
        operation_description="This endpoint initializes the counts for a user based on the user type.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_type", "user_id"],
            properties={
                "user_type": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户类型：1-游客，2-注册用户。"
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID。"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="The response data.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="The ID of the user.",
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        # user_type 1: 游客 2：注册用户
        user_type = data.get("user_type")
        user_id = data.get("user_id")

        sql_init_user_count = (
            f"INSERT INTO {settings.DEFAULT_DB}.pu_user_count (user_type, user_id, AI35_count, AI40_count, dalle_2_count, "
            f"baidu_drawing_count ) VALUES (%s,%s,%s,%s,%s,%s)")

        if int(user_type) == 1:

            params = (
                user_type,
                user_id,
                settings.VISITOR_AI35,
                settings.VISITOR_AI40,
                settings.VISITOR_DALLE2,
                settings.VISITOR_BAIDU_DRAWING,
            )
        else:
            # 查询游客状态下该用户的次数, 用户注册后送的次数要加上之前游客状态下剩余的次数

            sql_fetch_count_mode_visotor = (
                f"SELECT AI35_count, AI40_count, dalle_2_count, baidu_drawing_count FROM "
                f"{settings.DEFAULT_DB}.pu_user_count WHERE user_id = {user_id} AND "
                f"user_type = 1 LIMIT 1")

            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_fetch_count_mode_visotor)
                    query_data = MysqlOper.get_query_result(cursor)
                    if query_data:
                        query_data = query_data[0]
                        # AI35 暂时免费试用
                        AI35_count = query_data.get("AI35_count")
                        AI40_count = query_data.get("AI40_count")
                        dalle_2_count = query_data.get("dalle_2_count")
                        baidu_drawing_count = query_data.get(
                            "baidu_drawing_count")
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        raise CstException(code=code, message=message)

            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)

            params = (
                user_type,
                user_id,
                settings.REG_AI35,
                settings.REG_AI40 + int(AI40_count),
                settings.REG_DALLE2 + int(dalle_2_count),
                settings.REG_BAIDU_DRAWING + int(baidu_drawing_count),
            )

        logger.info(sql_init_user_count)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_init_user_count, params)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)

                    ret_data = {"user_id": user_id}

                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


# 暂时弃用
class UserCountManage(APIView):
    @swagger_auto_schema(
        operation_id="19",
        tags=["获取用户次数【新】"],
        operation_summary="获取用户次数",
        operation_description="根据用户ID获取用户的次数信息。",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="用户ID",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "AI35_count": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="AI35次数。"
                                ),
                                "AI40_count": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="AI40次数。"
                                ),
                                "dalle_2_count": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="DALLE-2次数。"
                                ),
                                "baidu_drawing_count": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="百度绘图次数。"
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        data = request.GET
        user_id = data.get("user_id")
        user_type = data.get("user_type")

        sql_fetch_user_counts = (
            f"SELECT AI35_count, AI40_count, dalle_2_count, baidu_drawing_count FROM "
            f"{settings.DEFAULT_DB}.pu_user_count WHERE user_id = '{user_id}' AND user_type = {user_type} "
            f"AND is_delete = 0 LIMIT 1")

        logger.info(sql_fetch_user_counts)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_user_counts)
                query_data = cursor.fetchone()
                if query_data:
                    AI35_count = query_data[0]
                    AI40_count = query_data[1]
                    dalle_2_count = query_data[2]
                    baidu_drawing_count = query_data[3]
                    code = RET.OK
                    message = Language.get(code)
                    ret_data = {
                        "AI35_count": AI35_count,
                        "AI40_count": AI40_count,
                        "dalle_2_count": dalle_2_count,
                        "baidu_drawing_count": baidu_drawing_count,
                    }
                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.NO_SUCH_USER
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    return CstResponse(code=code, message=message, data=[])

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    # 前端调用， 每天新登陆调用
    @swagger_auto_schema(
        operation_id="20",
        tags=["增加用户次数【新】"],
        operation_summary="增加用户次数",
        operation_description="为用户增加次数。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户ID。"
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")

        sql_update_count = (
            f"UPDATE {settings.DEFAULT_DB}.pu_user_count SET AI40_count = AI40_count + 2, "
            f" dalle_2_count = dalle_2_count + 2, baidu_drawing_count = baidu_drawing_count + 2"
            f" WHERE user_id = {user_id} AND user_type = 2 AND is_delete = 0")

        logger.error(sql_update_count)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update_count)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)

                    ret_data = {"user_id": user_id}

                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="21",
        tags=["减少用户次数【新】"],
        operation_summary="减少用户次数",
        operation_description="为用户减少次数。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "operate_count", "operate_type"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID。"
                ),
                "operate_count": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="操作次数。"
                ),
                "operate_type": openapi.Schema(
                    type=openapi.TYPE_STRING, description="操作类型。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="用户ID。"
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def put(self, request):

        data = request.data

        user_id = data.get("user_id")
        operate_count = data.get("operate_count")
        # operate_type 1: AI35 2:AI40, 3:DALLE-2 4:BAIDU_DRAWING
        map_operate_type = {
            "1": "AI35_count",
            "2": "AI40_count",
            "3": "dalle_2_count",
            "4": "baidu_drawing_count",
        }
        operate_type = data.get("operate_type")

        operate_field = map_operate_type.get(operate_type)

        sql_update_count = (
            f"UPDATE {settings.DEFAULT_DB}.pu_user_count SET {operate_field} = {operate_field} - {operate_count} "
            f"WHERE user_id = {user_id} AND is_delete = 0")

        logger.info(sql_update_count)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update_count)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    code = RET.OK
                    message = Language.get(code)

                    ret_data = {"user_id": user_id}

                    return CstResponse(
                        code=code, message=message, data=[ret_data])
                else:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class UserCountManageRedis(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redis = get_redis_connection("usage")

    @swagger_auto_schema(
        operation_id="23",
        tags=["用户次数管理【新】"],
        operation_summary="获取用户当前所有剩余次数【新】。",
        operation_description="redis key 存储格式[hset] name: {user_id: order_id} key: {prod_id: operate_type: flag }"
                              'value: {json {"expire_date":"", "value": }} ',
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID。",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总数。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "AI35": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "AI40": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "DALLE-2": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "BAIDU_DRAWING": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")

        # total_rest_count = settings.VIP_FRAME_LIMIT
        total_rest_count = defaultdict(dict)

        sql_check_vip = (
            f"SELECT 1 FROM {settings.DEFAULT_DB}.pm_membership WHERE user_id = '{user_id}' AND UNIX_TIMESTAMP(NOW()) < expire_at "
            f"AND status = 1 ORDER BY expire_at DESC LIMIT 1")

        logger.error(sql_check_vip)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_check_vip)
                rowcount = cursor.rowcount

                if rowcount > 0:
                    check_current_vip_content = (
                        f"SELECT oi.prod_id, o.order_id FROM {settings.DEFAULT_DB}.po_orders_items oi INNER JOIN po_orders o ON "
                        f"oi.order_id = o.order_id WHERE o.user_id = {user_id} AND o.status = 2 AND oi.prod_cate_id = 3 ORDER BY o.created_at DESC")

                    with connection.cursor() as cursor:
                        logger.error(check_current_vip_content)
                        cursor.execute(check_current_vip_content)
                        result = MysqlOper.get_query_result(cursor)

                        if not result:
                            code = RET.VIP_EXPIRED
                            message = Language.get(code)
                            return CstResponse(
                                code=code,
                                message=message,
                                data=settings.VIP_FRAME_LIMIT,
                            )

                        order_id = result[0].get("order_id")
                        prod_id = result[0].get("prod_id")
                        check_name = f"{user_id}:{order_id}"

                        check_redis_inited = None
                        for key in settings.NEW_ADD_PRODUCTS:
                            check_key = f"{int(prod_id)}:{key}:day"
                            check_redis_inited = self.redis.hget(
                                check_name, check_key)

                        if check_redis_inited is None:

                            # 取出上一个订单id， 获取redis 里用户id:order_id
                            # 下剩余的次数，初始化的时候加上剩余次数
                            sql_get_last_order = (
                                f"SELECT order_id FROM {settings.DEFAULT_DB}.po_orders WHERE status = 2 AND "
                                f"user_id = {user_id} ORDER BY created_at DESC LIMIT 2 ")

                            try:

                                with connection.cursor() as cursor:
                                    logger.error(sql_get_last_order)
                                    cursor.execute(sql_get_last_order)
                                    result_last_order = MysqlOper.get_query_result(
                                        cursor)
                                    # 确认是有上个order_id
                                    if len(result_last_order) > 1:

                                        last_order_id = result_last_order[1].get(
                                            "order_id")
                                    else:
                                        last_order_id = ""
                                print(last_order_id)
                            except Exception:
                                print(traceback.format_exc())
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                raise CstException(code=code, message=message)
                            try:
                                print(prod_id)
                                print("123456")
                                for prod_name in settings.VIP_FRAME_LIMIT_USAGE[
                                    int(prod_id)
                                ]:
                                    limit_content = settings.VIP_FRAME_LIMIT_USAGE[
                                        int(prod_id)
                                    ][prod_name]
                                    for limit_flag in limit_content:

                                        vip_limit_usage_name_last_order = (
                                            f"{user_id}:{last_order_id}"
                                        )
                                        vip_limit_usage_name = f"{user_id}:{order_id}"
                                        vip_limit_usage_hash_key = (
                                            f"{prod_id}:{prod_name}:{limit_flag}"
                                        )

                                        if limit_flag == "day":
                                            # 查询上个order_id 下对应的剩余的没有过期的次数
                                            if last_order_id:
                                                last_order_rest_count = self.redis.hget(
                                                    vip_limit_usage_name_last_order, vip_limit_usage_hash_key, )
                                                if last_order_rest_count:

                                                    last_order_rest_count_detail = (
                                                        json.loads(
                                                            last_order_rest_count
                                                        )
                                                    )
                                                    db_expire_date = last_order_rest_count_detail.get(
                                                        "expire_date")
                                                    db_rest_count = last_order_rest_count_detail.get(
                                                        "value")
                                                    have_rest_count = (
                                                        gadgets.is_expired_count(db_expire_date))

                                                    if have_rest_count:
                                                        db_rest_count = int(
                                                            db_rest_count
                                                        )
                                                    else:
                                                        db_rest_count = 0
                                                else:
                                                    db_rest_count = 0

                                                # 正常的过期时间
                                                expire_date = (
                                                    datetime.datetime.now().replace(
                                                        hour=23, minute=59, second=59, microsecond=0, ))

                                            else:
                                                expire_date = (
                                                    datetime.datetime.now().replace(
                                                        hour=23, minute=59, second=59, microsecond=0, ))
                                                db_rest_count = 0

                                        elif limit_flag == "week":

                                            if last_order_id:
                                                last_order_rest_count = self.redis.hget(
                                                    vip_limit_usage_name_last_order, vip_limit_usage_hash_key, )
                                                if last_order_rest_count:
                                                    last_order_rest_count_detail = (
                                                        json.loads(
                                                            last_order_rest_count
                                                        )
                                                    )
                                                    db_expire_date = last_order_rest_count_detail.get(
                                                        "expire_date")
                                                    db_rest_count = last_order_rest_count_detail.get(
                                                        "value")
                                                    have_rest_count = (
                                                        gadgets.is_expired_count(db_expire_date))

                                                    if have_rest_count:
                                                        db_rest_count = int(
                                                            db_rest_count
                                                        )
                                                    else:
                                                        db_rest_count = 0
                                                else:
                                                    db_rest_count = 0

                                                # 计算一周后的日期时间
                                                expire_date = (
                                                        datetime.datetime.now() +
                                                        datetime.timedelta(
                                                            weeks=1))

                                            else:
                                                expire_date = (
                                                        datetime.datetime.now() +
                                                        datetime.timedelta(
                                                            weeks=1))
                                                db_rest_count = 0

                                        elif limit_flag == "month":
                                            if last_order_id:
                                                last_order_rest_count = self.redis.hget(
                                                    vip_limit_usage_name_last_order, vip_limit_usage_hash_key, )
                                                if last_order_rest_count:
                                                    last_order_rest_count_detail = (
                                                        json.loads(
                                                            last_order_rest_count
                                                        )
                                                    )
                                                    db_expire_date = last_order_rest_count_detail.get(
                                                        "expire_date")
                                                    db_rest_count = last_order_rest_count_detail.get(
                                                        "value")
                                                    have_rest_count = (
                                                        gadgets.is_expired_count(db_expire_date))

                                                    if have_rest_count:
                                                        db_rest_count = int(
                                                            db_rest_count
                                                        )
                                                    else:
                                                        db_rest_count = 0
                                                else:
                                                    db_rest_count = 0

                                                # 计算一个月后的日期时间
                                                expire_date = (
                                                        datetime.datetime.now() +
                                                        datetime.timedelta(
                                                            days=30))

                                            else:
                                                expire_date = (
                                                        datetime.datetime.now() +
                                                        datetime.timedelta(
                                                            days=30))
                                                db_rest_count = 0
                                        vip_limit_usage_hash_value = {
                                            "expire_date": expire_date,
                                            "value": limit_content[limit_flag]
                                                     + db_rest_count,
                                        }

                                        try:
                                            self.redis.hset(
                                                vip_limit_usage_name,
                                                vip_limit_usage_hash_key,
                                                json.dumps(
                                                    vip_limit_usage_hash_value,
                                                    cls=DateTimeEncoder,
                                                    ensure_ascii=False,
                                                ),
                                            )

                                        except Exception:
                                            code = RET.DB_ERR
                                            message = Language.get(code)
                                            trace = str(traceback.format_exc())
                                            logger.error(trace)
                                            raise CstException(
                                                code=code, message=message
                                            )

                            except Exception:
                                print(traceback.format_exc())
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                raise CstException(code=code, message=message)

                        for (
                                each_operate_target_key,
                                each_operate_target_value,
                        ) in settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)].items():
                            flags = list(each_operate_target_value.keys())

                            print(flags)
                            print("flagsflagsflagsflags")
                            try:
                                for flag in flags:
                                    check_name = f"{user_id}:{order_id}"
                                    check_key = f"{int(prod_id)}:{each_operate_target_key}:{flag}"
                                    rest_value = self.redis.hget(
                                        check_name, check_key)

                                    print(check_name)
                                    print(check_key)
                                    print(rest_value)
                                    if rest_value:
                                        rest_value = json.loads(rest_value)
                                        total_rest_count[each_operate_target_key][
                                            flag
                                        ] = rest_value.get("value")
                                    else:
                                        total_rest_count[each_operate_target_key][
                                            flag
                                        ] = 0

                            except Exception:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                raise CstException(code=code, message=message)
                        code = RET.OK
                        message = Language.get(code)

                        return CstResponse(
                            data=total_rest_count, code=code, message=message
                        )

                else:
                    code = RET.VIP_EXPIRED
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    return CstResponse(
                        code=code,
                        message=message,
                        data=settings.VIP_FRAME_LIMIT)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    # 暂时废弃
    # def get(self, request):
    #     user_id = request.query_params.get('user_id')
    #
    #     # total_rest_count = settings.VIP_FRAME_LIMIT
    #     total_rest_count = defaultdict(dict)
    #
    #     sql_check_vip = f"SELECT 1 FROM {settings.DEFAULT_DB}.pm_membership WHERE user_id = '{user_id}' AND UNIX_TIMESTAMP(NOW()) < expire_at " \
    #                     f"AND status = 1 ORDER BY expire_at DESC LIMIT 1"
    #
    #     logger.error(sql_check_vip)
    #
    #     try:
    #         with connection.cursor() as cursor:
    #             cursor.execute(sql_check_vip)
    #             rowcount = cursor.rowcount
    #
    #             if rowcount > 0:
    #                 check_current_vip_content = f"SELECT oi.prod_id, o.order_id FROM {settings.DEFAULT_DB}.po_orders_items oi INNER JOIN po_orders o ON " \
    #                                             f"oi.order_id = o.order_id WHERE o.user_id = {user_id} AND o.status = 2 AND oi.prod_cate_id = 3 ORDER BY o.created_at DESC"
    #
    #                 with connection.cursor() as cursor:
    #                     logger.error(check_current_vip_content)
    #                     cursor.execute(check_current_vip_content)
    #                     result = MysqlOper.get_query_result(cursor)
    #
    #                     if not result:
    #                         code = RET.VIP_EXPIRED
    #                         message = Language.get(code)
    #                         return CstResponse(code=code, message=message, data=settings.VIP_FRAME_LIMIT)
    #
    #                     order_id = result[0].get('order_id')
    #                     prod_id = result[0].get('prod_id')
    #                     check_name = f"{user_id}:{order_id}"
    #
    #                     check_redis_inited = None
    #                     for key in settings.NEW_ADD_PRODUCTS:
    #                         check_key = f"{int(prod_id)}:{key}:day"
    #                         check_redis_inited = self.redis.hget(check_name, check_key)
    #
    #                     if check_redis_inited is None:
    #
    #                         # 取出上一个订单id， 获取redis 里用户id:order_id 下剩余的次数，初始化的时候加上剩余次数
    #                         sql_get_last_order = f"SELECT order_id FROM {settings.DEFAULT_DB}.po_orders WHERE status = 2 AND " \
    #                                              f"user_id = {user_id} ORDER BY created_at DESC LIMIT 2 "
    #
    #                         try:
    #
    #                             with connection.cursor() as cursor:
    #                                 logger.error(sql_get_last_order)
    #                                 cursor.execute(sql_get_last_order)
    #                                 result_last_order = MysqlOper.get_query_result(cursor)
    #                                 # 确认是有上个order_id
    #                                 if len(result_last_order) > 1:
    #
    #                                     last_order_id = result_last_order[1].get('order_id')
    #                                 else:
    #                                     last_order_id = ''
    #                             print(last_order_id)
    #                         except Exception:
    #                             print(traceback.format_exc())
    #                             code = RET.DB_ERR
    #                             message = Language.get(code)
    #                             trace = str(traceback.format_exc())
    #                             logger.error(trace)
    #                             raise CstException(code=code, message=message)
    #                         try:
    #                             print(prod_id)
    #                             print('123456')
    #                             for prod_name in settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)]:
    #                                 limit_content = settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)][prod_name]
    #                                 for limit_flag in limit_content:
    #
    #                                     vip_limit_usage_name_last_order = f"{user_id}:{last_order_id}"
    #                                     vip_limit_usage_name = f"{user_id}:{order_id}"
    #                                     vip_limit_usage_hash_key = f"{prod_id}:{prod_name}:{limit_flag}"
    #
    #                                     if limit_flag == 'day':
    #                                         # 查询上个order_id 下对应的剩余的没有过期的次数
    #                                         if last_order_id:
    #                                             last_order_rest_count = self.redis.hget(vip_limit_usage_name_last_order,
    #                                                                                     vip_limit_usage_hash_key)
    #                                             if last_order_rest_count:
    #
    #                                                 last_order_rest_count_detail = json.loads(last_order_rest_count)
    #                                                 db_expire_date = last_order_rest_count_detail.get('expire_date')
    #                                                 db_rest_count = last_order_rest_count_detail.get('value')
    #                                                 have_rest_count = gadgets.is_expired_count(db_expire_date)
    #
    #                                                 if have_rest_count:
    #                                                     db_rest_count = int(db_rest_count)
    #                                                 else:
    #                                                     db_rest_count = 0
    #                                             else:
    #                                                 db_rest_count = 0
    #
    #                                             # 正常的过期时间
    #                                             expire_date = datetime.datetime.now().replace(hour=23, minute=59,
    #                                                                                           second=59, microsecond=0)
    #
    #                                         else:
    #                                             expire_date = datetime.datetime.now().replace(hour=23, minute=59,
    #                                                                                           second=59, microsecond=0)
    #                                             db_rest_count = 0
    #
    #                                     elif limit_flag == 'week':
    #
    #                                         if last_order_id:
    #                                             last_order_rest_count = self.redis.hget(vip_limit_usage_name_last_order,
    #                                                                                     vip_limit_usage_hash_key)
    #                                             if last_order_rest_count:
    #                                                 last_order_rest_count_detail = json.loads(last_order_rest_count)
    #                                                 db_expire_date = last_order_rest_count_detail.get('expire_date')
    #                                                 db_rest_count = last_order_rest_count_detail.get('value')
    #                                                 have_rest_count = gadgets.is_expired_count(db_expire_date)
    #
    #                                                 if have_rest_count:
    #                                                     db_rest_count = int(db_rest_count)
    #                                                 else:
    #                                                     db_rest_count = 0
    #                                             else:
    #                                                 db_rest_count = 0
    #
    #                                             # 计算一周后的日期时间
    #                                             expire_date = datetime.datetime.now() + datetime.timedelta(weeks=1)
    #
    #                                         else:
    #                                             expire_date = datetime.datetime.now() + datetime.timedelta(weeks=1)
    #                                             db_rest_count = 0
    #
    #                                     elif limit_flag == 'month':
    #                                         if last_order_id:
    #                                             last_order_rest_count = self.redis.hget(vip_limit_usage_name_last_order,
    #                                                                                     vip_limit_usage_hash_key)
    #                                             if last_order_rest_count:
    #                                                 last_order_rest_count_detail = json.loads(last_order_rest_count)
    #                                                 db_expire_date = last_order_rest_count_detail.get('expire_date')
    #                                                 db_rest_count = last_order_rest_count_detail.get('value')
    #                                                 have_rest_count = gadgets.is_expired_count(db_expire_date)
    #
    #                                                 if have_rest_count:
    #                                                     db_rest_count = int(db_rest_count)
    #                                                 else:
    #                                                     db_rest_count = 0
    #                                             else:
    #                                                 db_rest_count = 0
    #
    #                                             # 计算一个月后的日期时间
    #                                             expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
    #
    #                                         else:
    #                                             expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
    #                                             db_rest_count = 0
    #                                     vip_limit_usage_hash_value = {
    #                                         'expire_date': expire_date,
    #                                         'value': limit_content[limit_flag] + db_rest_count
    #                                     }
    #
    #                                     try:
    #                                         self.redis.hset(vip_limit_usage_name, vip_limit_usage_hash_key,
    #                                                         json.dumps(vip_limit_usage_hash_value,
    #                                                                    cls=DateTimeEncoder,
    #                                                                    ensure_ascii=False))
    #
    #                                     except Exception:
    #                                         code = RET.DB_ERR
    #                                         message = Language.get(code)
    #                                         trace = str(traceback.format_exc())
    #                                         logger.error(trace)
    #                                         raise CstException(code=code, message=message)
    #
    #                         except Exception:
    #                             print(traceback.format_exc())
    #                             code = RET.DB_ERR
    #                             message = Language.get(code)
    #                             trace = str(traceback.format_exc())
    #                             logger.error(trace)
    #                             raise CstException(code=code, message=message)
    #
    #                     for each_operate_target_key, each_operate_target_value in settings.VIP_FRAME_LIMIT_USAGE[
    #                         int(prod_id)].items():
    #                         flags = list(each_operate_target_value.keys())
    #
    #                         print(flags)
    #                         print('flagsflagsflagsflags')
    #                         try:
    #                             for flag in flags:
    #                                 check_name = f"{user_id}:{order_id}"
    #                                 check_key = f"{int(prod_id)}:{each_operate_target_key}:{flag}"
    #                                 rest_value = self.redis.hget(check_name, check_key)
    #
    #                                 print(check_name)
    #                                 print(check_key)
    #                                 print(rest_value)
    #                                 if rest_value:
    #                                     rest_value = json.loads(rest_value)
    #                                     total_rest_count[each_operate_target_key][flag] = rest_value.get("value")
    #                                 else:
    #                                     total_rest_count[each_operate_target_key][flag] = 0
    #
    #                         except Exception:
    #                             code = RET.DB_ERR
    #                             message = Language.get(code)
    #                             trace = str(traceback.format_exc())
    #                             logger.error(trace)
    #                             raise CstException(code=code, message=message)
    #                     code = RET.OK
    #                     message = Language.get(code)
    #
    #                     return CstResponse(data=total_rest_count, code=code, message=message)
    #
    #             else:
    #                 code = RET.VIP_EXPIRED
    #                 message = Language.get(code)
    #                 trace = str(traceback.format_exc())
    #                 logger.error(trace)
    #                 return CstResponse(code=code, message=message, data=settings.VIP_FRAME_LIMIT)
    #
    #     except Exception:
    #         code = RET.DB_ERR
    #         message = Language.get(code)
    #         trace = str(traceback.format_exc())
    #         logger.error(trace)
    #         raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="22",
        tags=["用户次数管理【新】"],
        operation_summary="用户次数增减。",
        operation_description="redis key 存储格式[hset] name: {user_id: order_id} key: {prod_id: operate_type: flag }"
                              'value: {json {"expire_date":"", "value": }} ',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "operate_count", "operate_type"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID。"
                ),
                "operate_count": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="操作次数。"
                ),
                "operate_type": openapi.Schema(
                    type=openapi.TYPE_STRING, description="操作类型。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "month": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="月限额。"
                                ),
                                "week": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="周限额。"
                                ),
                                "day": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="天限额。"
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")

        operate_count = data.get("operate_count")

        # operate_type 1: AI35 2:AI40, 3:DALLE-2 4:BAIDU_DRAWING
        map_operate_type = {
            "1": "AI35",
            "2": "AI40",
            "3": "DALLE_2",
            "4": "BAIDU_DRAWING",
            "5": "WENXIN",
            "6": "XUNFEI",
            "7": "MJ",
            "8": "CLAUDE",
            "9": "CHATGLM",
            "10": "STABLEDIFFUSION",
            "11": "QIANWEN",
            "12": "SENSECORE",
            "13": "360",
        }
        operate_type = data.get("operate_type")
        operate_target = map_operate_type.get(operate_type)

        sql_check_vip = (
            f"SELECT expire_at  FROM {settings.DEFAULT_DB}.pm_membership WHERE user_id = '{user_id}' "
            f" AND  status = 1 ORDER BY expire_at DESC LIMIT 1")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_check_vip)
                result = MysqlOper.get_query_result(cursor)

                if result:
                    expire_at = result[0].get("expire_at")
                    if int(time.time()) > int(expire_at):
                        expire_at_bool = True
                    else:
                        expire_at_bool = False

                else:
                    expire_at_bool = False

                if expire_at_bool:
                    sql_update_status = f"UPDATE {settings.DEFAULT_DB}.pm_membership SET status = 2 WHERE user_id = '{user_id}'"
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_update_status)
                            rowcount = cursor.rowcount
                            # 会员过期
                            if rowcount > 0:
                                code = RET.VIP_EXPIRED
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.info(trace)
                                return CstResponse(code=code, message=message)

                            else:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                trace = str(traceback.format_exc())
                                logger.error(trace)
                                raise CstException(code=code, message=message)

                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        raise CstException(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        check_current_vip_content = (
            f"SELECT oi.prod_id, o.order_id FROM po_orders_items oi INNER JOIN po_orders o ON "
            f"oi.order_id = o.order_id WHERE o.user_id = {user_id} AND o.status = 2"
            f" AND oi.prod_cate_id = 3 ORDER BY o.created_at DESC  ")

        try:
            with connection.cursor() as cursor:
                cursor.execute(check_current_vip_content)
                result = MysqlOper.get_query_result(cursor)

                if result:
                    order_id = result[0].get("order_id")
                    prod_id = result[0].get("prod_id")
                    total_rest_count = defaultdict(dict)
                    current_time = datetime.datetime.now()
                    for prod_name, limit_content in settings.VIP_FRAME_LIMIT_USAGE[
                        int(prod_id)
                    ].items():
                        if prod_name != operate_target:
                            continue

                        for limit_flag, limit_value in limit_content.items():
                            vip_limit_usage_name = f"{user_id}:{order_id}"
                            vip_limit_usage_hash_key = (
                                f"{prod_id}:{prod_name}:{limit_flag}"
                            )
                            vip_limit_usage_hash_value = self.redis.hget(
                                vip_limit_usage_name, vip_limit_usage_hash_key
                            )

                            if vip_limit_usage_hash_value:

                                vip_limit_usage_hash_value = json.loads(
                                    vip_limit_usage_hash_value
                                )
                                vip_limit_usage_hash_value_expired_date = (
                                    vip_limit_usage_hash_value.get("expire_date")
                                )
                                vip_limit_usage_hash_value_expired_date = (
                                    datetime.datetime.fromisoformat(
                                        vip_limit_usage_hash_value_expired_date
                                    )
                                )
                                vip_limit_usage_hash_value_data = int(
                                    vip_limit_usage_hash_value.get("value")
                                )

                                if limit_flag == "day":
                                    day_expire_date = datetime.datetime.now().replace(
                                        hour=23, minute=59, second=59, microsecond=0)
                                    vip_limit_usage_hash_value_day = {
                                        "expire_date": day_expire_date.isoformat(),
                                        "value": limit_content[limit_flag],
                                    }

                                    if (current_time >
                                            vip_limit_usage_hash_value_expired_date):
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_day,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )
                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_day["value"]
                                    else:
                                        vip_limit_usage_hash_value_day[
                                            "value"
                                        ] = vip_limit_usage_hash_value_data - int(
                                            operate_count
                                        )
                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_day["value"]
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_day,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )

                                elif limit_flag == "week":
                                    week_expire_date = (
                                            datetime.datetime.now()
                                            + datetime.timedelta(weeks=1)
                                    )
                                    vip_limit_usage_hash_value_week = {
                                        "expire_date": week_expire_date.isoformat(),
                                        "value": limit_content[limit_flag],
                                    }

                                    if (current_time >
                                            vip_limit_usage_hash_value_expired_date):
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_week,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )

                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_week["value"]

                                    else:
                                        vip_limit_usage_hash_value_week[
                                            "value"
                                        ] = vip_limit_usage_hash_value_data - int(
                                            operate_count
                                        )
                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_week["value"]
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_week,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )

                                elif limit_flag == "month":
                                    month_expire_date = (
                                            datetime.datetime.now()
                                            + datetime.timedelta(days=30)
                                    )
                                    vip_limit_usage_hash_value_month = {
                                        "expire_date": month_expire_date.isoformat(),
                                        "value": limit_content[limit_flag],
                                    }

                                    if (current_time >
                                            vip_limit_usage_hash_value_expired_date):
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_month,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )

                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_month["value"]

                                    else:
                                        vip_limit_usage_hash_value_month[
                                            "value"
                                        ] = vip_limit_usage_hash_value_data - int(
                                            operate_count
                                        )
                                        total_rest_count[operate_target][
                                            limit_flag
                                        ] = vip_limit_usage_hash_value_month["value"]
                                        self.redis.hset(
                                            vip_limit_usage_name,
                                            vip_limit_usage_hash_key,
                                            json.dumps(
                                                vip_limit_usage_hash_value_month,
                                                cls=DateTimeEncoder,
                                                ensure_ascii=False,
                                            ),
                                        )

                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(
                        data=total_rest_count[operate_target],
                        code=code,
                        message=message,
                    )

                else:
                    code = RET.VIP_EXPIRED
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    return CstResponse(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class UserCountManageRedisNoVip(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redis = get_redis_connection("usage")

    @swagger_auto_schema(
        operation_id="25",
        tags=["赠送次数-0224需求"],
        operation_summary="获取当前剩余次数",
        operation_description="redis key 存储格式[hset] name: {user_id } key: {prod_id: operate_type: flag }"
                              'value: {json {"expire_date":"", "value": }} ',
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID。",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "user_type",
                openapi.IN_QUERY,
                description="用户类型。",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总数。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "AI35": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "AI40": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "DALLE-2": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "BAIDU_DRAWING": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")
        user_type = request.query_params.get("user_type")

        # 保持redis数据格式统一， 游客 order_id = 1  注册用户 order_id = 2 vip 为真实order_id

        if int(user_type) == 1:
            order_id = 1
        else:
            order_id = 2

        if int(user_type) == 1:
            prod_id = 9
        else:
            prod_id = 10

        check_name = f"{user_id}:{order_id}"

        check_redis_inited = None
        for key in settings.NEW_ADD_PRODUCTS:
            check_key = f"{int(prod_id)}:{key}:day"
            check_redis_inited = self.redis.hget(check_name, check_key)

        if check_redis_inited is None:
            try:
                for prod_name in settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)]:
                    limit_content = settings.VIP_FRAME_LIMIT_USAGE[int(
                        prod_id)][prod_name]
                    for limit_flag in limit_content:

                        vip_limit_usage_name = f"{user_id}:{order_id}"
                        vip_limit_usage_hash_key = f"{prod_id}:{prod_name}:{limit_flag}"

                        if limit_flag == "day":
                            expire_date = datetime.datetime.now().replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                        elif limit_flag == "week":
                            # 计算一周后的日期时间
                            expire_date = datetime.datetime.now() + datetime.timedelta(
                                weeks=1
                            )
                        elif limit_flag == "month":
                            # 计算一个月后的日期时间
                            expire_date = datetime.datetime.now() + datetime.timedelta(
                                days=30
                            )

                        vip_limit_usage_hash_value = {
                            "expire_date": expire_date,
                            "value": limit_content[limit_flag],
                        }

                        try:
                            self.redis.hset(
                                vip_limit_usage_name,
                                vip_limit_usage_hash_key,
                                json.dumps(
                                    vip_limit_usage_hash_value,
                                    cls=DateTimeEncoder,
                                    ensure_ascii=False,
                                ),
                            )

                        except Exception:
                            code = RET.DB_ERR
                            message = Language.get(code)
                            trace = str(traceback.format_exc())
                            logger.error(trace)
                            raise CstException(code=code, message=message)
            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)

        total_rest_count = defaultdict(dict)
        for (
                each_operate_target_key,
                each_operate_target_value,
        ) in settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)].items():
            flags = list(each_operate_target_value.keys())
            try:
                for flag in flags:
                    check_name = f"{user_id}:{order_id}"
                    check_key = f"{int(prod_id)}:{each_operate_target_key}:{flag}"
                    rest_value = self.redis.hget(check_name, check_key)
                    if rest_value:
                        rest_value = json.loads(rest_value)
                        total_rest_count[each_operate_target_key][
                            flag
                        ] = rest_value.get("value")
                    else:
                        code = RET.USER_ABNORMAL
                        message = Language.get(code)
                        return CstResponse(code=code, message=message)
            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)
        code = RET.OK
        message = Language.get(code)

        return CstResponse(data=total_rest_count, code=code, message=message)

    @swagger_auto_schema(
        operation_id="26",
        tags=["赠送次数-0224需求"],
        operation_summary="用户次数增减。",
        operation_description="redis key 存储格式[hset] name: {user_id: order_id} key: {prod_id: operate_type: flag }"
                              'value: {json {"expire_date":"", "value": }} ',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "operate_count", "operate_type"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户ID。"
                ),
                "operate_count": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="操作次数。"
                ),
                "operate_type": openapi.Schema(
                    type=openapi.TYPE_STRING, description="操作类型。"
                ),
                "user_type": openapi.Schema(
                    type=openapi.TYPE_STRING, description="用户类型。"
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
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "month": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="月限额。"
                                ),
                                "week": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="周限额。"
                                ),
                                "day": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="天限额。"
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")

        user_type = data.get("user_type")

        # 保持redis数据格式统一， 游客 order_id = 1  注册用户 order_id = 2 vip 为真实order_id

        if int(user_type) == 1:
            order_id = 1
        else:
            order_id = 2

        if int(user_type) == 1:
            prod_id = 9
        else:
            prod_id = 10

        operate_count = data.get("operate_count")
        # operate_type 1: AI35 2:AI40, 3:DALLE-2 4:BAIDU_DRAWING
        map_operate_type = {
            "1": "AI35",
            "2": "AI40",
            "3": "DALLE_2",
            "4": "BAIDU_DRAWING",
            "5": "WENXIN",
            "6": "XUNFEI",
            "7": "MJ",
            "8": "CLAUDE",
            "9": "CHATGLM",
            "10": "STABLEDIFFUSION",
            "11": "QIANWEN",
            "12": "SENSECORE",
            "13": "360",
        }
        operate_type = data.get("operate_type")
        operate_target = map_operate_type.get(operate_type)

        total_rest_count = defaultdict(dict)
        current_time = datetime.datetime.now()

        for prod_name, limit_content in settings.VIP_FRAME_LIMIT_USAGE[
            int(prod_id)
        ].items():
            if prod_name != operate_target:
                continue

            for limit_flag, limit_value in limit_content.items():
                try:
                    vip_limit_usage_name = f"{user_id}:{order_id}"
                    vip_limit_usage_hash_key = f"{prod_id}:{prod_name}:{limit_flag}"
                    vip_limit_usage_hash_value = self.redis.hget(
                        vip_limit_usage_name, vip_limit_usage_hash_key
                    )

                    if vip_limit_usage_hash_value:
                        vip_limit_usage_hash_value = json.loads(
                            vip_limit_usage_hash_value
                        )
                        vip_limit_usage_hash_value_expired_date = (
                            vip_limit_usage_hash_value.get("expire_date")
                        )
                        vip_limit_usage_hash_value_expired_date = (
                            datetime.datetime.fromisoformat(
                                vip_limit_usage_hash_value_expired_date
                            )
                        )
                        vip_limit_usage_hash_value_data = int(
                            vip_limit_usage_hash_value.get("value")
                        )

                        if limit_flag == "day":
                            day_expire_date = datetime.datetime.now().replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                            vip_limit_usage_hash_value_day = {
                                "expire_date": day_expire_date.isoformat(),
                                "value": limit_content[limit_flag],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_day,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[operate_target][
                                    limit_flag
                                ] = vip_limit_usage_hash_value_day["value"]

                            else:
                                vip_limit_usage_hash_value_day[
                                    "value"
                                ] = vip_limit_usage_hash_value_data - int(operate_count)
                                total_rest_count[operate_target][limit_flag] = (
                                    vip_limit_usage_hash_value_day["value"]
                                    if vip_limit_usage_hash_value_day["value"] > 0
                                    else 0
                                )

                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_day,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                        elif limit_flag == "week":
                            week_expire_date = (
                                    datetime.datetime.now() +
                                    datetime.timedelta(
                                        weeks=1))
                            vip_limit_usage_hash_value_week = {
                                "expire_date": week_expire_date.isoformat(),
                                "value": limit_content[limit_flag],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_week,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[operate_target][limit_flag] = (
                                    vip_limit_usage_hash_value_week["value"]
                                    if vip_limit_usage_hash_value_week["value"] >= 0
                                    else 0
                                )

                            else:
                                vip_limit_usage_hash_value_week[
                                    "value"
                                ] = vip_limit_usage_hash_value_data - int(operate_count)
                                total_rest_count[operate_target][limit_flag] = (
                                    vip_limit_usage_hash_value_week["value"]
                                    if vip_limit_usage_hash_value_week["value"] > 0
                                    else 0
                                )
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_week,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                        elif limit_flag == "month":
                            month_expire_date = (
                                    datetime.datetime.now() +
                                    datetime.timedelta(
                                        days=30))
                            vip_limit_usage_hash_value_month = {
                                "expire_date": month_expire_date.isoformat(),
                                "value": limit_content[limit_flag],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_month,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[operate_target][limit_flag] = (
                                    vip_limit_usage_hash_value_month["value"]
                                    if vip_limit_usage_hash_value_month["value"] >= 0
                                    else 0
                                )

                            else:
                                vip_limit_usage_hash_value_month[
                                    "value"
                                ] = vip_limit_usage_hash_value_data - int(operate_count)
                                total_rest_count[operate_target][limit_flag] = (
                                    vip_limit_usage_hash_value_month["value"]
                                    if vip_limit_usage_hash_value_month["value"] > 0
                                    else 0
                                )

                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_month,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                except Exception:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        code = RET.OK
        message = Language.get(code)
        trace = str(traceback.format_exc())
        logger.error(trace)
        return CstResponse(code=code, data=total_rest_count, message=message)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "action": openapi.Schema(type=openapi.TYPE_INTEGER),
                "user_type": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
            required=["user_id", "action", "user_type"],
        ),
        operation_summary="赠送次数",
        operation_description="赠送次数",
        tags=["赠送次数-0224需求"],
        operation_id="28",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息。"
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="总数。"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "AI35": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "AI40": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "DALLE-2": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                                "BAIDU_DRAWING": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "month": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="月限额。",
                                        ),
                                        "week": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="周限额。",
                                        ),
                                        "day": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="天限额。",
                                        ),
                                    },
                                ),
                            },
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
                            type=openapi.TYPE_INTEGER, description="错误代码。"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息。"
                        ),
                    },
                ),
            ),
        },
    )
    def put(self, request):

        data = request.data

        user_id = data.get("user_id")
        action = data.get("action")
        user_type = data.get("user_type")

        # 保持redis数据格式统一， 游客 order_id = 1  注册用户 order_id = 2 vip 为真实order_id

        if int(user_type) == 1:
            order_id = 1
        else:
            order_id = 2

        if int(user_type) == 1:
            prod_id = 9
        else:
            prod_id = 10

        # 1:每天登陆 2: 转发 3: 分销赠送
        if int(action) == 1:
            quota_value = settings.QUOTA_FRAME[1]
        elif int(action) == 3:
            quota_value = settings.QUOTA_FRAME[3]
        else:
            quota_value = settings.QUOTA_FRAME[2]

        total_rest_count = defaultdict(dict)
        current_time = datetime.datetime.now()

        check_name = f"{user_id}:{order_id}"

        check_redis_inited = None
        for key in settings.NEW_ADD_PRODUCTS:
            check_key = f"{int(prod_id)}:{key}:day"
            check_redis_inited = self.redis.hget(check_name, check_key)

        if check_redis_inited is None:
            try:
                for prod_name in settings.VIP_FRAME_LIMIT_USAGE[int(prod_id)]:
                    limit_content = settings.VIP_FRAME_LIMIT_USAGE[int(
                        prod_id)][prod_name]
                    for limit_flag in limit_content:

                        vip_limit_usage_name = f"{user_id}:{order_id}"
                        vip_limit_usage_hash_key = f"{prod_id}:{prod_name}:{limit_flag}"

                        if limit_flag == "day":
                            expire_date = datetime.datetime.now().replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                        elif limit_flag == "week":
                            # 计算一周后的日期时间
                            expire_date = datetime.datetime.now() + datetime.timedelta(
                                weeks=1
                            )
                        elif limit_flag == "month":
                            # 计算一个月后的日期时间
                            expire_date = datetime.datetime.now() + datetime.timedelta(
                                days=30
                            )

                        vip_limit_usage_hash_value = {
                            "expire_date": expire_date,
                            "value": limit_content[limit_flag],
                        }

                        try:
                            self.redis.hset(
                                vip_limit_usage_name,
                                vip_limit_usage_hash_key,
                                json.dumps(
                                    vip_limit_usage_hash_value,
                                    cls=DateTimeEncoder,
                                    ensure_ascii=False,
                                ),
                            )

                        except Exception:
                            code = RET.DB_ERR
                            message = Language.get(code)
                            trace = str(traceback.format_exc())
                            logger.error(trace)
                            raise CstException(code=code, message=message)
            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                raise CstException(code=code, message=message)

        for prod_name, limit_content in settings.VIP_FRAME_LIMIT_USAGE[
            int(prod_id)
        ].items():
            # if prod_name != operate_target:
            #     continue
            for limit_flag, limit_value in limit_content.items():
                try:
                    vip_limit_usage_name = f"{user_id}:{order_id}"
                    vip_limit_usage_hash_key = f"{prod_id}:{prod_name}:{limit_flag}"
                    vip_limit_usage_hash_value = self.redis.hget(
                        vip_limit_usage_name, vip_limit_usage_hash_key
                    )

                    if vip_limit_usage_hash_value:
                        vip_limit_usage_hash_value = json.loads(
                            vip_limit_usage_hash_value
                        )
                        vip_limit_usage_hash_value_expired_date = (
                            vip_limit_usage_hash_value.get("expire_date")
                        )
                        vip_limit_usage_hash_value_expired_date = (
                            datetime.datetime.fromisoformat(
                                vip_limit_usage_hash_value_expired_date
                            )
                        )
                        vip_limit_usage_hash_value_data = int(
                            vip_limit_usage_hash_value.get("value")
                        )

                        if limit_flag == "day":
                            day_expire_date = datetime.datetime.now().replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                            vip_limit_usage_hash_value_day = {
                                "expire_date": day_expire_date.isoformat(),
                                "value": quota_value[prod_name],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_day,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[prod_name][
                                    limit_flag
                                ] = vip_limit_usage_hash_value_day["value"]

                            else:
                                vip_limit_usage_hash_value_day["value"] = (
                                        vip_limit_usage_hash_value_data
                                        + quota_value[prod_name]
                                )
                                total_rest_count[prod_name][limit_flag] = (
                                    vip_limit_usage_hash_value_day["value"]
                                    if vip_limit_usage_hash_value_day["value"] > 0
                                    else 0
                                )

                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_day,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                        elif limit_flag == "week":
                            week_expire_date = (
                                    datetime.datetime.now() +
                                    datetime.timedelta(
                                        weeks=1))
                            vip_limit_usage_hash_value_week = {
                                "expire_date": week_expire_date.isoformat(),
                                "value": quota_value[prod_name],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_week,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[prod_name][limit_flag] = (
                                    vip_limit_usage_hash_value_week["value"]
                                    if vip_limit_usage_hash_value_week["value"] >= 0
                                    else 0
                                )

                            else:
                                vip_limit_usage_hash_value_week["value"] = (
                                        vip_limit_usage_hash_value_data
                                        + quota_value[prod_name]
                                )
                                total_rest_count[prod_name][limit_flag] = (
                                    vip_limit_usage_hash_value_week["value"]
                                    if vip_limit_usage_hash_value_week["value"] > 0
                                    else 0
                                )
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_week,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                        elif limit_flag == "month":
                            month_expire_date = (
                                    datetime.datetime.now() +
                                    datetime.timedelta(
                                        days=30))
                            vip_limit_usage_hash_value_month = {
                                "expire_date": month_expire_date.isoformat(),
                                "value": quota_value[prod_name],
                            }

                            if current_time > vip_limit_usage_hash_value_expired_date:
                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_month,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )

                                total_rest_count[prod_name][limit_flag] = (
                                    vip_limit_usage_hash_value_month["value"]
                                    if vip_limit_usage_hash_value_month["value"] >= 0
                                    else 0
                                )

                            else:
                                vip_limit_usage_hash_value_month["value"] = (
                                        vip_limit_usage_hash_value_data
                                        + quota_value[prod_name]
                                )
                                total_rest_count[prod_name][limit_flag] = (
                                    vip_limit_usage_hash_value_month["value"]
                                    if vip_limit_usage_hash_value_month["value"] > 0
                                    else 0
                                )

                                self.redis.hset(
                                    vip_limit_usage_name,
                                    vip_limit_usage_hash_key,
                                    json.dumps(
                                        vip_limit_usage_hash_value_month,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                    ),
                                )
                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        raise CstException(code=code, message=message)

                except Exception:
                    code = RET.DB_ERR
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    raise CstException(code=code, message=message)

        code = RET.OK
        message = Language.get(code)
        trace = str(traceback.format_exc())
        logger.error(trace)
        return CstResponse(code=code, data=total_rest_count, message=message)


class ActivateCodeConsume(APIView):
    @swagger_auto_schema(
        operation_id="22",
        tags=["v3.1"],
        operation_summary="卡密核销",
        operation_description="卡密核销。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "activate_code": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="激活码"
                ),
            },
            required=["activate_code"],
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="成功代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="成功消息"
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="产品列表",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "activate_code": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="核销掉的激活码"
                                    ),
                                    "user_id,": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="用户id"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="错误请求",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
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
                            type=openapi.TYPE_INTEGER, description="错误代码"
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="错误消息"
                        ),
                    },
                ),
            ),
        },
    )
    @transaction.atomic()
    @csrf_exempt
    @ExperienceCardRejectSecPurchase(
        param={"db": settings.DEFAULT_DB, "logger": logger}
    )
    def post(self, request):

        worker_id = 1004
        data = request.data
        user_id = data.get("user_id")
        activate_code = data.get("activate_code")
        order_id = get_distributed_id(worker_id)
        order_status = 1

        print(22222)
        # # 检查是否已经是会员状态
        # sql_check_vip = f"SELECT expire_at FROM {settings.DEFAULT_DB}.pm_membership WHERE user_id = '{user_id}' " \
        #                 f"AND UNIX_TIMESTAMP(NOW()) < expire_at AND status = 1 ORDER BY expire_at DESC LIMIT 1"
        # logger.error(sql_check_vip)
        # try:
        #     with connection.cursor() as cursor:
        #         cursor.execute(sql_check_vip)
        #         result = MysqlOper.get_query_result(cursor)
        #         if result:
        #             expire_at = result[0].get('expire_at')
        #             already_vip = 1
        #         else:
        #             already_vip = 0
        #             expire_at = 0
        #
        # except Exception:
        #     code = RET.CODE_EXPIRED
        #     message = Language.get(code)
        #     trace = str(traceback.format_exc())
        #     logger.error(trace)
        #     return CstResponse(code=code, message=message)

        save_id = transaction.savepoint()

        # check activate_code details
        sql_code_status = (
            f"SELECT activate_code_id, generated_by, to_prod_id, status, expired_date FROM "
            f"{settings.ADMIN_DB}.oa_activate_code WHERE activate_code = '{activate_code}' AND "
            f" NOW() < expired_date AND is_delete = 0")

        try:
            logger.info(sql_code_status)
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_code_status)
                result = MysqlOper.get_query_result(cursor)

                if result:

                    result = result[0]
                    code_status = result.get("status")
                    if int(code_status) == 1:
                        code = RET.CODE_CONSUMED
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)
                        return CstResponse(code=code, message=message)
                    else:
                        to_prod_id = result.get("to_prod_id")
                else:
                    code = RET.CODE_INVALID
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)
                    return CstResponse(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        # 跨表查询code 对应产品价格
        sql_check_code_price = (
            f"SELECT prod_price, prod_cate_id FROM {settings.DEFAULT_DB}.pp_products WHERE prod_id={to_prod_id} "
            f"AND is_delete = 0")

        try:
            logger.info(sql_check_code_price)
            with connection.cursor() as cursor:
                cursor.execute(sql_check_code_price)
                result = MysqlOper.get_query_result(cursor)

                if result:
                    result = result[0]
                    price = result.get("prod_price")
                    prod_cate_id = result.get("prod_cate_id")
                else:
                    code = RET.CODE_EXPIRED
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)
                    return CstResponse(code=code, message=message)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_order = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders (order_id, user_id, total_amount, status, prod_cate_id ) "
            f" VALUES ({order_id}, {user_id}, {price}, {order_status}, {prod_cate_id})")
        try:
            logger.info(unpaid_sql_order)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_order)
                unpaid_row_count_order = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_orders_items = (
            f"INSERT INTO {settings.DEFAULT_DB}.po_orders_items (order_id, prod_id, quantity, price, prod_cate_id) "
            f" VALUES ({order_id}, {to_prod_id},1,  {price}, {prod_cate_id}) ")

        try:
            logger.info(unpaid_sql_orders_items)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_orders_items)
                unpaid_row_orders_items = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        unpaid_sql_payments = (
            f"INSERT INTO {settings.DEFAULT_DB}.pp_payments (order_id, user_id, amount, status, payment_method, pay_data) "
            f" VALUES ({order_id}, {user_id},{price}, 0, 3, '')")

        try:
            logger.info(unpaid_sql_payments)
            with connection.cursor() as cursor:
                cursor.execute(unpaid_sql_payments)
                unpaid_row_sql_payments = cursor.rowcount

        except Exception:
            code = RET.ORDER_CREATE_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            transaction.savepoint_rollback(save_id)
            raise CstException(code=code, message=message)

        if (unpaid_row_count_order +
                unpaid_row_orders_items +
                unpaid_row_sql_payments == 3):
            # 插入阶段预提交
            transaction.savepoint_commit(save_id)
            pay_id = get_distributed_id(worker_id=worker_id)

            update_payment = f"UPDATE {settings.DEFAULT_DB}.pp_payments SET status = 1, pay_id = {pay_id} WHERE order_id = {order_id}"
            update_order = f"UPDATE {settings.DEFAULT_DB}.po_orders SET status = 2, processed = 1  WHERE order_id = {order_id}"
            # 更新消费者id
            update_code_table = f"UPDATE {settings.ADMIN_DB}.oa_activate_code SET consumed_by = {user_id}, status = 1 WHERE activate_code = '{activate_code}'"

            try:
                with connection.cursor() as cursor:
                    logger.error(update_payment)
                    cursor.execute(update_payment)
                    update_payment_rowcount = cursor.rowcount

                with connection.cursor() as cursor:
                    logger.error(update_order)
                    cursor.execute(update_order)
                    update_order_rowcount = cursor.rowcount

                with connections[settings.ADMIN_DB].cursor() as cursor:
                    logger.error(update_code_table)
                    cursor.execute(update_code_table)
                    update_code_rowcount = cursor.rowcount

                if (
                        update_payment_rowcount
                        + update_order_rowcount
                        + update_code_rowcount
                        == 3
                ):
                    user_active_data = {"user_id": user_id}

                    req_url_active = (
                            settings.SERVER_BILL_URL
                            + ":"
                            + settings.SERVER_BILL_PORT
                            + settings.IS_ACTIVE_ADDRESS
                    )
                    user_active_req = requests.post(
                        url=req_url_active, data=user_active_data
                    )

                    if user_active_req.status_code == 200:
                        user_active_req_data = json.loads(user_active_req.text)
                        if user_active_req_data.get("code") == 20000:
                            user_is_active = user_active_req_data.get("data")
                        else:
                            user_is_active = False
                    else:
                        user_is_active = False

                    print(user_is_active)
                    print("user_is_activeuser_is_activeuser_is_activeuser_is_active")
                    if user_is_active:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_RENEW
                        )
                    else:
                        req_url = (
                                settings.SERVER_BILL_URL
                                + ":"
                                + settings.SERVER_BILL_PORT
                                + settings.HASHRATE_ADDRESS
                        )

                    insert_member_success = False
                    insert_package_success = False
                    # 会员类别，写入会员有效期等数据和写入算力值&算力值有效期
                    if int(prod_cate_id) == 3:
                        insert_member_config = gadgets.insert_new_member(
                            order_id=order_id, conn=connection, pay=True
                        )

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": to_prod_id,
                            "quantity": 1,
                            "prod_cate_id": prod_cate_id,
                        }
                        print(hashrate_data)
                        print(req_url)
                        print("req_urlreq_urlreq_urlreq_urlreq_url")
                        insert_member_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        print(insert_member_hashrate_req.status_code)
                        print(
                            "insert_member_hashrate_req.status_codeinsert_member_hashrate_req.status_codeinsert_member_hashrate_req.status_code"
                        )
                        if insert_member_hashrate_req.status_code == 200:

                            insert_member_hashrate_data = json.loads(
                                insert_member_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                print(insert_member_hashrate_data)
                                print(
                                    "insert_member_hashrate_datainsert_member_hashrate_data"
                                )
                                insert_member_hashrate = True
                            else:
                                insert_member_hashrate = False
                        else:
                            insert_member_hashrate = False

                        if insert_member_config and insert_member_hashrate:
                            insert_member_success = True
                            insert_package_success = True
                        else:
                            insert_member_success = False
                            insert_package_success = False
                    # 流量包写入算力值和算力值有效期
                    elif int(prod_cate_id) == 6:

                        hashrate_data = {
                            "user_id": user_id,
                            "prod_id": to_prod_id,
                            "quantity": 1,
                            "prod_cate_id": prod_cate_id,
                        }
                        insert_package_hashrate_req = requests.post(
                            url=req_url, data=hashrate_data
                        )
                        if insert_package_hashrate_req.status_code == 200:
                            insert_member_hashrate_data = json.loads(
                                insert_package_hashrate_req.text
                            )
                            if insert_member_hashrate_data.get(
                                    "code") == 20000:
                                insert_package_success = True
                                insert_member_success = True
                    else:
                        # 非会员和流量包外的其他逻辑
                        insert_member_success = True
                        insert_package_success = True

                    if insert_member_success and insert_package_success:
                        code = RET.OK
                        message = Language.get(code)
                        # 追踪提交
                        # transaction.savepoint_commit()
                        return CstResponse(
                            data={"activate_code": activate_code},
                            code=code,
                            message=message,
                        )

                    else:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        trace = str(traceback.format_exc())
                        logger.error(trace)
                        transaction.savepoint_rollback(save_id)

                        raise CstException(code=code, message=message)
                else:

                    code = RET.CODE_INVALID
                    message = Language.get(code)
                    trace = str(traceback.format_exc())
                    logger.error(trace)
                    transaction.savepoint_rollback(save_id)

                    raise CstException(code=code, message=message)

            except Exception:
                code = RET.CODE_INVALID
                message = Language.get(code)
                trace = str(traceback.format_exc())
                logger.error(trace)
                transaction.savepoint_rollback(save_id)

                raise CstException(code=code, message=message)


class PicturesManage(APIView):
    @swagger_auto_schema(
        operation_id="30",
        tags=["图片"],
        operation_summary="图片",
        operation_description="This endpoint allows users to submit their business cooperation details.",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of submitted cooperation details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片名称."
                                    ),
                                    "pic_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片id."
                                    ),
                                    "pic_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片描述."
                                    ),
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片类型."
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):

        sql_get_pics = f"SELECT pic_id, pic_url, pic_desc,type FROM {settings.DEFAULT_DB}.op_pictures WHERE type in (" \
                       f"1,2,3,4,8) AND is_delete = 0 "

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_pics)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["pic_id"] = each.get("pic_id")
                    data_dict["pic_url"] = settings.OSS_PREFIX + \
                                           each.get("pic_url")
                    data_dict["pic_desc"] = each.get("pic_desc")
                    data_dict["type"] = each.get("type")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            raise CstException(code=code, message=message)


class QuestionsSetManage(APIView):
    serializer_class = QuestionsSetManageSerializer

    @swagger_auto_schema(
        operation_id="31",
        tags=["v2.1"],
        operation_summary="问题集",
        operation_description="此端点允许用户获取问题集详情。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="所属行业ID."
                ),
                "occupation_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="所属职业ID."
                ),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="所属二级职业ID."
                ),
                "emp_duration_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="从业时间ID."
                ),
                "expertise_level_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="专业水平ID."
                ),
                "module_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="module_id."
                ),
            },
        ),
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
                            description="提交的问题集详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "question_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题ID."
                                    ),
                                    "module_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属模块ID."
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题标题."
                                    ),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题内容."
                                    ),
                                    "content_hidden": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="隐藏内容."
                                    ),
                                    "industry_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属行业ID."
                                    ),
                                    "occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属职业ID."
                                    ),
                                    "sub_occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="所属二级职业ID.",
                                    ),
                                    "emp_duration_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间ID."
                                    ),
                                    "expertise_level_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平ID."
                                    ),
                                },
                            ),
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
    # @cache_response(timeout=settings.CACHE_TIME, key_func=CstKeyConstructor(), cache='cache')
    def post(self, request):

        industry_id = request.data.get("industry_id", None)
        occu_id = request.data.get("occu_id", None)
        sub_occu_id = request.data.get("sub_occu_id", None)
        emp_duration_id = request.data.get("emp_duration_id", None)
        expertise_level_id = request.data.get("expertise_level_id", None)
        module_id = request.data.get("module_id", None)
        page_count = request.data.get("page_count", None)
        page_index = request.data.get("page_index", None)

        sql_get_question_set = (
            f"SELECT a.question_id, a.module_id, a.title,a.content,a.example_question, b.contact_qr_code,"
            f"b.contact_qr_code_desc, "
            f" b.interest_group, b.interest_group_desc, c.character_avatar, "
            f" a.industry_id, a.occupation_id, a.sub_occu_id, "
            f"a.emp_duration_id, a.expertise_level_id, a.content_hidden FROM {settings.ADMIN_DB}.op_questions_set a "
            f"LEFT JOIN {settings.ADMIN_DB}.op_modules b ON a.module_id = b.module_id "
            f"LEFT JOIN {settings.ADMIN_DB}.uqd_user_question_details c ON a.question_id = c.question_id AND c.is_delete = 0 "
            f"WHERE a.industry_id = {industry_id}  AND a.is_delete = 0  AND a.is_hidden = 0  ")

        sql_get_question_set_total = (
            f"SELECT count(*) as total FROM {settings.ADMIN_DB}.op_questions_set "
            f"WHERE industry_id = {industry_id} AND module_id = {module_id} AND is_delete = 0 AND is_hidden = 0 ")

        if occu_id is not None:
            sql_get_question_set += f"AND a.occupation_id = {occu_id} "
            sql_get_question_set_total += f"AND occupation_id = {occu_id} "

        if sub_occu_id is not None:
            sql_get_question_set += f"AND a.sub_occu_id = {sub_occu_id} "
            sql_get_question_set_total += f"AND sub_occu_id = {sub_occu_id} "

        if emp_duration_id is not None:
            sql_get_question_set += f"AND a.emp_duration_id = {emp_duration_id} "
            sql_get_question_set_total += f"AND emp_duration_id = {emp_duration_id} "

        if expertise_level_id is not None:
            sql_get_question_set += f"AND a.expertise_level_id = {expertise_level_id} "
            sql_get_question_set_total += (
                f"AND expertise_level_id = {expertise_level_id} "
            )

        if module_id is not None:
            sql_get_question_set += f"AND a.module_id = {module_id} "

        if page_count is not None:
            sql_get_question_set += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_question_set += " OFFSET " + str(row_index)

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_question_set_total)
                result = MysqlOper.get_query_result(cursor)
                total = result[0].get("total")
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            # 添加异常事件
            raise CstException(code=code, message=message)

        try:
            logger.error(sql_get_question_set)
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_question_set)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["question_id"] = each.get("question_id")
                    data_dict["module_id"] = each.get("module_id")
                    data_dict["title"] = each.get("title")
                    data_dict["content"] = each.get("content")
                    data_dict["example_question"] = each.get(
                        "example_question")
                    data_dict["contact_qr_code"] = each.get("contact_qr_code")
                    data_dict["contact_qr_code_desc"] = each.get(
                        "contact_qr_code_desc", ""
                    )
                    data_dict["interest_group_code"] = each.get(
                        "interest_group")
                    data_dict["interest_group_code_desc"] = each.get(
                        "interest_group_desc", ""
                    )
                    data_dict["content_hidden"] = each.get("content_hidden")
                    data_dict["industry_id"] = each.get("industry_id")
                    data_dict["occupation_id"] = each.get("occupation_id")
                    data_dict["character_avatar"] = each.get(
                        "character_avatar")
                    data_dict["sub_occu_id"] = each.get("sub_occu_id")
                    data_dict["emp_duration_id"] = each.get("emp_duration_id")
                    data_dict["expertise_level_id"] = each.get(
                        "expertise_level_id")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(
                    code=code, message=message, data=ret_data, total=total
                )
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)

    def get(self, request):
        data = request.GET
        question_id = data.get("question_id")
        module_id = data.get("module_id")

        sql_get_question_set = (
            f"SELECT a.question_id, a.module_id, a.example_question, a.title,a.content, b.contact_qr_code,b.contact_qr_code_desc,"
            f" b.interest_group, b.interest_group_desc,  "
            f" a.industry_id, a.occupation_id, a.sub_occu_id, "
            f"a.emp_duration_id, a.expertise_level_id, a.content_hidden FROM {settings.ADMIN_DB}.op_questions_set a "
            f"LEFT JOIN {settings.ADMIN_DB}.op_modules b ON a.module_id = b.module_id "
            f"WHERE a.question_id = '{question_id}' AND a.module_id = '{module_id}' AND a.is_delete = 0  AND a.is_hidden = 0 ")

        try:
            logger.error(sql_get_question_set)
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_question_set)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["question_id"] = each.get("question_id")
                    data_dict["module_id"] = each.get("module_id")
                    data_dict["title"] = each.get("title")
                    data_dict["content"] = each.get("content")
                    data_dict["example_question"] = each.get(
                        "example_question")
                    data_dict["contact_qr_code"] = each.get("contact_qr_code")
                    data_dict["contact_qr_code_desc"] = each.get(
                        "contact_qr_code_desc", ""
                    )
                    data_dict["interest_group_code"] = each.get(
                        "interest_group")
                    data_dict["interest_group_code_desc"] = each.get(
                        "interest_group_desc", ""
                    )
                    data_dict["content_hidden"] = each.get("content_hidden")
                    data_dict["industry_id"] = each.get("industry_id")
                    data_dict["occupation_id"] = each.get("occupation_id")
                    data_dict["sub_occu_id"] = each.get("sub_occu_id")
                    data_dict["emp_duration_id"] = each.get("emp_duration_id")
                    data_dict["expertise_level_id"] = each.get(
                        "expertise_level_id")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class IndustryManage(APIView):
    @swagger_auto_schema(
        operation_id="32",
        tags=["v2.1"],
        operation_summary="行业",
        operation_description="此端点允许用户获取行业详情。",
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
                            description="提交的行业详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "industry_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="行业ID."
                                    ),
                                    "industry_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="行业名称."
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="创建时间."
                                    ),
                                    "updated_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="更新时间."
                                    ),
                                },
                            ),
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
    @cache_response(timeout=settings.CACHE_TIME,
                    key_func=CstKeyConstructor(), cache="cache")
    def get(self, request):

        sql_get_industry = (
            f"SELECT industry_id, name, description, naics_code, sic_code FROM {settings.ADMIN_DB}."
            f"op_industry WHERE is_delete = 0 AND is_hidden = 0 AND industry_id NOT IN (1003, 1004) ")

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_industry)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["industry_id"] = each.get("industry_id")
                    data_dict["name"] = each.get("name")
                    data_dict["description"] = each.get("description")
                    data_dict["naics_code"] = each.get("naics_code")
                    data_dict["sic_code"] = each.get("sic_code")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class TabManage(APIView):
    @swagger_auto_schema(
        operation_id="v5.2",
        tags=["v5.2"],
        operation_summary="tab栏",
        operation_description="此端点允许用户获取行业详情。",
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
                            description="提交的tab栏详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "tab_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="tab ID."
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="tab 名称."
                                    ),
                                    "icon": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="icon 名称."
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="创建时间."
                                    ),
                                    "updated_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="更新时间."
                                    ),
                                },
                            ),
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
    # @cache_response(timeout=settings.CACHE_TIME, key_func=CstKeyConstructor(), cache='cache')
    def get(self, request):

        sql_get_industry = (
            f"SELECT tab_id, name, description, icon, weight  FROM {settings.ADMIN_DB}."
            f"op_tab WHERE is_delete = 0 AND is_hidden = 0 ORDER BY weight  ")

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_industry)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["weight"] = each.get("weight")
                    data_dict["tab_id"] = each.get("tab_id")
                    data_dict["name"] = each.get("name")
                    data_dict["icon"] = each.get("icon")
                    data_dict["description"] = each.get("description")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class OccupationManage(APIView):
    @swagger_auto_schema(
        operation_id="34",
        tags=["v3.1"],
        operation_summary="职业",
        operation_description="此端点允许用户根据行业ID提交并获取职业详情。s",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="所属行业ID"
                ),
            },
        ),
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
                            description="提交的职业详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="职业ID."
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="职业名称."
                                    ),
                                    "description": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="职业描述."
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="创建时间."
                                    ),
                                    "updated_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="更新时间."
                                    ),
                                },
                            ),
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
    @cache_response(timeout=settings.CACHE_TIME,
                    key_func=CstKeyConstructor(), cache="cache")
    def post(self, request):
        industry_id = request.data.get("industry_id")

        sql_get_occupation = (
            f"SELECT occu_id, name, description FROM {settings.ADMIN_DB}."
            f"op_occupation WHERE industry_id = %s AND is_delete = 0 AND is_hidden = 0 ")

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_occupation, [industry_id])

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["occu_id"] = each.get("occu_id")
                    data_dict["name"] = each.get("name")
                    data_dict["description"] = each.get("description")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class SubOccupationManage(APIView):
    @swagger_auto_schema(
        operation_id="35",
        tags=["v2.1"],
        operation_summary="子职业",
        operation_description="此端点允许用户根据行业ID和主职业ID提交并获取子职业详情。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="所属行业ID"
                ),
                "occu_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="主职业ID"
                ),
            },
        ),
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
                            description="提交的子职业详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "sub_occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="子职业ID."
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="子职业名称."
                                    ),
                                    "description": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="子职业描述."
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="创建时间."
                                    ),
                                    "updated_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="更新时间."
                                    ),
                                },
                            ),
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
    @cache_response(timeout=settings.CACHE_TIME,
                    key_func=CstKeyConstructor(), cache="cache")
    def post(self, request):
        industry_id = request.data.get("industry_id")
        occu_id = request.data.get("occu_id")

        sql_get_sub_occu = (
            f"SELECT sub_occu_id, name, description FROM {settings.ADMIN_DB}.op_sub_occu "
            f"WHERE industry_id = %s AND occu_id = %s AND is_delete = 0 AND is_hidden = 0  ")

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_sub_occu, [industry_id, occu_id])

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["sub_occu_id"] = each.get("sub_occu_id")
                    data_dict["name"] = each.get("name")
                    data_dict["description"] = each.get("description")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class EmpDurationManage(APIView):
    @swagger_auto_schema(
        operation_id="50",
        tags=["v2.1"],
        operation_summary="从业时间",
        operation_description="This endpoint allows users to get the employment duration details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="行业ID"
                ),
                "occu_id": openapi.Schema(type=openapi.TYPE_STRING, description="职业ID"),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="子职业ID"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of employment duration details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "emp_duration_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间ID"
                                    ),
                                    "emp_duration_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间名称"
                                    ),
                                    "emp_duration_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间描述"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    @cache_response(timeout=settings.CACHE_TIME,
                    key_func=CstKeyConstructor(), cache="cache")
    def post(self, request):
        industry_id = request.data.get("industry_id", None)
        occu_id = request.data.get("occu_id", None)
        sub_occu_id = request.data.get("sub_occu_id", None)

        sql_conditions = []
        if industry_id is not None:
            sql_conditions.append(f"industry_id = '{industry_id}'")
        if occu_id is not None:
            sql_conditions.append(f"occu_id = '{occu_id}'")
        if sub_occu_id is not None:
            sql_conditions.append(f"sub_occu_id = '{sub_occu_id}'")

        if sql_conditions:
            sql_conditions_str = " AND ".join(sql_conditions)
            sql_get_emp_durations = (
                f"SELECT  emp_duration_id, emp_duration_name, emp_duration_desc FROM "
                f"{settings.ADMIN_DB}.op_emp_duration WHERE {sql_conditions_str} AND is_delete = 0 AND is_hidden = 0  ")
        else:
            sql_get_emp_durations = (
                f"SELECT  emp_duration_id, emp_duration_name, emp_duration_desc FROM "
                f"{settings.ADMIN_DB}.op_emp_duration WHERE is_delete = 0  AND is_hidden = 0 ")

        logger.error(sql_get_emp_durations)
        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_emp_durations)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["emp_duration_id"] = each.get("emp_duration_id")
                    data_dict["emp_duration_name"] = each.get(
                        "emp_duration_name")
                    data_dict["emp_duration_desc"] = each.get(
                        "emp_duration_desc")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class ExpertiseLevelManage(APIView):
    @swagger_auto_schema(
        operation_id="51",
        tags=["v2.1"],
        operation_summary="专业水平",
        operation_description="This endpoint allows users to get the expertise level details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="行业ID"
                ),
                "occu_id": openapi.Schema(type=openapi.TYPE_STRING, description="职业ID"),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="子职业ID"
                ),
                "emp_duration_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="从业时间ID"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of expertise level details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "expertise_level_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平ID"
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平名称"
                                    ),
                                    "description": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平描述"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    @cache_response(timeout=settings.CACHE_TIME,
                    key_func=CstKeyConstructor(), cache="cache")
    def post(self, request):
        industry_id = request.data.get("industry_id", None)
        occu_id = request.data.get("occu_id", None)
        sub_occu_id = request.data.get("sub_occu_id", None)
        emp_duration_id = request.data.get("emp_duration_id", None)

        sql_conditions = []
        if industry_id is not None:
            sql_conditions.append(f"industry_id = '{industry_id}'")
        if occu_id is not None:
            sql_conditions.append(f"occu_id = '{occu_id}'")
        if sub_occu_id is not None:
            sql_conditions.append(f"sub_occu_id = '{sub_occu_id}'")
        if emp_duration_id is not None:
            sql_conditions.append(f"emp_duration_id = '{emp_duration_id}'")

        if sql_conditions:
            sql_conditions_str = " AND ".join(sql_conditions)
            sql_get_expertise_levels = (
                f"SELECT expertise_level_id, name, description FROM {settings.ADMIN_DB}."
                f"op_expertise_level WHERE is_delete = 0 AND is_hidden = 0  AND {sql_conditions_str} ")
        else:
            sql_get_expertise_levels = (
                f"SELECT expertise_level_id, name, description FROM {settings.ADMIN_DB}."
                f"op_expertise_level WHERE is_delete = 0 AND is_hidden = 0 ")

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_expertise_levels)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["expertise_level_id"] = each.get(
                        "expertise_level_id")
                    data_dict["name"] = each.get("name")
                    data_dict["description"] = each.get("description")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class OpModulesManage(APIView):
    @swagger_auto_schema(
        operation_id="52",
        tags=["v5.2"],
        operation_summary="模块",
        operation_description="This endpoint allows users to get the operation module details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="行业ID"
                ),
                "occu_id": openapi.Schema(type=openapi.TYPE_STRING, description="职业ID"),
                "sub_occu_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="子职业ID"
                ),
                "emp_duration_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="从业时间ID"
                ),
                "expertise_level_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="专业水平ID"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="A list of operation module details.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "module_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="模块ID"
                                    ),
                                    "name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="模块名称"
                                    ),
                                    "description": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="模块描述"
                                    ),
                                    "icon": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="模块icon"
                                    ),
                                },
                            ),
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    # @cache_response(timeout=settings.CACHE_TIME, key_func=CstKeyConstructor(), cache='cache')
    def post(self, request):
        try:
            conditions = {}
            for field in [
                "industry_id",
                "occu_id",
                "sub_occu_id",
                "emp_duration_id",
                "expertise_level_id",
            ]:
                value = request.data.get(field)
                if value is not None:
                    conditions[field] = value

            where_clauses = ["m.is_delete = 0", "m.is_hidden = 0"]
            where_clauses += [f"m.{key} = %s" for key in conditions.keys()]
            where_sql = " AND ".join(where_clauses)

            sql = f"""
                SELECT m.module_id, m.name, m.description, m.icon, COUNT(q.id) AS count
                FROM {settings.ADMIN_DB}.op_modules AS m
                LEFT JOIN {settings.ADMIN_DB}.op_questions_set AS q ON m.module_id = q.module_id
                WHERE {where_sql}
                GROUP BY m.module_id, m.name, m.description, m.icon;
                """

            print(sql)
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql, list(conditions.values()))

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["module_id"] = each.get("module_id")
                    data_dict["name"] = each.get("name")
                    data_dict["description"] = each.get("description")
                    data_dict["icon"] = (
                        settings.OSS_PREFIX + each.get("icon")
                        if not str(each.get("icon")).startswith("https")
                        else each.get("icon")
                    )
                    data_dict["count"] = each.get("count", 0)  # 新增的统计信息
                    ret_data.append(data_dict)

                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)

        except Exception as e:
            code = RET.DB_ERR
            message = Language.get(code)
            logger.error(str(e))
            raise CstException(code=code, message=message)


class TokenConsume(APIView):
    @swagger_auto_schema(
        operation_id="55",
        tags=["v3.1"],
        operation_summary="消耗用户的令牌",
        operation_description="消耗用户的特定产品的令牌，并更新用户的剩余令牌总数。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "prod_name", "consumed_token"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="产品名称"
                ),
                "consumed_token": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="消耗的令牌数量"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        r_prod_id_maps = get_redis_connection("config")
        r_usage = get_redis_connection("usage")
        user_id = request.data.get("user_id")
        prod_name = request.data.get("prod_name")
        consumed_token = request.data.get("consumed_token")
        consumed_token = int(consumed_token)
        prod_id_maps = json.loads(r_prod_id_maps.get("config:products:idMaps"))
        prod_id = prod_id_maps.get(prod_name)

        # 获取该用户购买的所有该类型的流量包的键值
        package_keys = r_usage.zrange(f"packages:{user_id}:{prod_id}", 0, -1)

        for earliest_package_key in package_keys:
            earliest_package_info = r_usage.hgetall(earliest_package_key)

            if earliest_package_info:
                count = int(earliest_package_info["count"])
                expire_at = float(earliest_package_info["expire_at"])

                # 检查是否已过期

                if (expire_at < datetime.datetime.now().timestamp()) or count <= 0:
                    # 已过期，从 Sorted Set 中删除
                    r_usage.zrem(
                        f"packages:{user_id}:{prod_id}",
                        earliest_package_key)
                    r_usage.decr(
                        f"total_count:{user_id}:{prod_id}", count
                    )  # 更新用户的总剩余次数
                    # 释放空间, 已经过期的没必要再留着了, mysql 中有订单记录可以用作回溯
                    # r_usage.delete(earliest_package_key)

                else:
                    # 如果未过期则跳出循环，开始使用流量包
                    break
        else:
            # 如果所有流量包都已过期，返回错误信息
            code = RET.USED_UP
            message = Language.get(code)
            return CstResponse(code=code, message=message)
        # 使用一次

        if count > 0:
            count -= int(consumed_token)
            count = max(count, 0)
            r_usage.hset(earliest_package_key, "count", count)
            total_count = int(
                r_usage.get(f"total_count:{user_id}:{prod_id}") or 0)
            if total_count > 0:
                total_count -= int(consumed_token)
                total_count = max(total_count, 0)
                r_usage.set(f"total_count:{user_id}:{prod_id}", total_count)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        else:
            code = RET.USED_UP
            message = Language.get(code)
            return CstResponse(code=code, message=message)

    @swagger_auto_schema(
        operation_id="56",
        tags=["v3.1"],
        operation_summary="获取用户的令牌总数",
        operation_description="获取用户所有产品的剩余令牌总数。",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            description="包含所有产品及其剩余令牌总数的列表。",
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")

        r_prod_id_maps = get_redis_connection("config")
        r_usage = get_redis_connection("usage")
        prod_id_maps = json.loads(r_prod_id_maps.get("config:products:idMaps"))
        ret_data = defaultdict(dict)

        for prod_name, prod_id in prod_id_maps.items():
            # 获取该用户购买的所有该类型的流量包的键值
            package_keys = r_usage.zrange(
                f"packages:{user_id}:{prod_id}", 0, -1)

            for earliest_package_key in package_keys:
                earliest_package_info = r_usage.hgetall(earliest_package_key)

                if earliest_package_info:
                    count = int(earliest_package_info["count"])
                    expire_at = float(earliest_package_info["expire_at"])

                    # 检查是否已过期
                    if expire_at < datetime.datetime.now().timestamp():
                        # 已过期，从 Sorted Set 中删除
                        r_usage.zrem(
                            f"packages:{user_id}:{prod_id}",
                            earliest_package_key)
                        r_usage.decr(
                            f"total_count:{user_id}:{prod_id}", count
                        )  # 更新用户的总剩余次数
                        # 释放空间, 已经过期的没必要再留着了, mysql 中有订单记录可以用作回溯
                        # r_usage.delete(earliest_package_key)
                    else:
                        # 如果未过期则跳出循环，开始使用流量包
                        break

            rest_count = r_usage.get(f"total_count:{user_id}:{prod_id}") or 0
            total_count = r_usage.get(
                f"total_count_origin:{user_id}:{prod_id}") or 0
            ret_data[prod_name]["rest"] = rest_count
            ret_data[prod_name]["total"] = total_count

        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=[ret_data])


class TokenConsumeUniversal(APIView):
    @swagger_auto_schema(
        operation_id="109",
        tags=["v3.1"],
        operation_summary="通用流量包扣费",
        operation_description="消耗用户的通用流量包的费用，并更新用户的剩余费用。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "prod_name", "consumed_token"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="用户ID"
                ),
                "prod_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="产品名称"
                ),
                "consumed_token": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="消耗的令牌数量"
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        r_prod_id_maps = get_redis_connection("config")
        r_usage = get_redis_connection("usage")
        user_id = request.data.get("user_id")
        prod_name = request.data.get("prod_name")
        consumed_token = request.data.get("consumed_token")
        consumed_token = int(consumed_token)
        getcontext().prec = 10

        # 所有可能的产品ID
        possible_prod_ids = [18, 19, 20, 21, 22, 23, 24, 25, 26]

        # 初始化最早的产品ID和时间戳
        earliest_prod_id = None
        earliest_timestamp = float("inf")

        for prod_id in possible_prod_ids:
            package_keys = r_usage.zrange(
                f"universal_packages:{user_id}:{prod_id}", 0, -1
            )

            print(package_keys)
            print("package_keyspackage_keyspackage_keyspackage_keyspackage_keys")
            if package_keys:
                for each_key in package_keys:
                    package_info = r_usage.hgetall(each_key)
                    if package_info:
                        timestamp = float(
                            package_info.get("expire_at", 0)
                        )  # 使用购买时间作为排序依据

                        # 计算消耗的价格
                        # product_config = json.loads(r_prod_id_maps.get(f'config:{prod_id}'))
                        # price_per_token = Decimal(product_config[prod_name]['price']) / Decimal(
                        #     product_config[prod_name]['tokens'])
                        # consumed_price = Decimal(consumed_token) * price_per_token
                        # consumed_price = consumed_price.quantize(Decimal('0.00000000'))
                        rest_total_price = Decimal(package_info["total_price"])

                        # 如果剩余总价足够支付消耗的价格，才将其视为有效的候选产品
                        if rest_total_price >= consumed_token:
                            if timestamp < earliest_timestamp:
                                print(package_info)
                                print("earliest package data")
                                earliest_timestamp = timestamp
                                earliest_prod_id = prod_id
                        else:
                            # 边界情况，如果剩余余额总数小于10积分且rest_total_price -
                            # consumed_token <=0, 允许用户使用最后一次
                            if int(rest_total_price) <= 10:
                                if timestamp < earliest_timestamp:
                                    print(package_info)
                                    print("earliest package data")
                                    earliest_timestamp = timestamp
                                    earliest_prod_id = prod_id

        print(earliest_prod_id)
        print("earliest_prod_idearliest_prod_idearliest_prod_idearliest_prod_id")
        # 如果没有找到任何产品
        if earliest_prod_id is None:
            code = RET.USED_UP
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        prod_id = earliest_prod_id

        # TODO prod_id 为 购买的所有 18,19,20,21 中时间靠前的 产品, 例如 我购买了 18 产品三份, 19 一份, 20 一份 21 一份,
        #  时间依次增大, 我在使用了 18 中的一份余额接近耗尽的时候又购买了一份 18 的产品, 那么 还是将其优先级排在 21 之后,
        #  因为他的购买时间晚于 21 的购买时间
        product_config = json.loads(r_prod_id_maps.get(f"config:{prod_id}"))

        # 获取该用户购买的所有该类型的流量包的键值
        package_keys = r_usage.zrange(
            f"universal_packages:{user_id}:{prod_id}", 0, -1)

        print(package_keys)
        print("lkljkkjkjkjkkj")
        for earliest_package_key in package_keys:
            print(earliest_package_key)
            print("12345678")
            earliest_package_info = r_usage.hgetall(earliest_package_key)

            if earliest_package_info:
                expire_at = float(earliest_package_info["expire_at"])
                rest_total_price = float(earliest_package_info["total_price"])

                print(earliest_package_info)
                print("earliest_package_infoearliest_package_infoearliest_package_info")
                print(rest_total_price)
                # 检查是否已过期
                if (
                        expire_at < datetime.datetime.now().timestamp()
                        or rest_total_price <= 1
                ):
                    print(f"current product {prod_id} used up")
                    # 已过期，从 Sorted Set 中删除
                    r_usage.zrem(
                        f"universal_packages:{user_id}:{prod_id}",
                        earliest_package_key)
                    r_usage.incrbyfloat(
                        f"total_price:{user_id}:{prod_id}", -rest_total_price
                    )  # 更新用户的总剩余次数

                    # 释放空间, 已经过期的没必要再留着了, mysql 中有订单记录可以用作回溯
                    # r_usage.delete(earliest_package_key)
                    continue

                # 如果该产品是通用流量包，则令牌数等于总价格除以每个令牌的价格
                if int(prod_id) in [18, 19, 20, 21, 22, 23, 24, 25, 26]:

                    prod_total_price = Decimal(
                        earliest_package_info["total_price"])
                    total_price = r_usage.get(
                        f"total_price:{user_id}:{prod_id}")
                    if prod_total_price >= consumed_token:
                        # 扣除费用
                        prod_total_price = prod_total_price - consumed_token
                        total_price = Decimal(total_price) - consumed_token
                        r_usage.hset(
                            earliest_package_key,
                            "total_price",
                            str(prod_total_price))
                        r_usage.set(
                            f"total_price:{user_id}:{prod_id}",
                            str(total_price))
                    else:
                        # print(111111111)
                        # total_price = Decimal(total_price) - consumed_price
                        # # 如果达到临界值， 则强制归位0.00
                        # if total_price < 0.009:
                        #     print(f'{user_id}, {prod_id} reached border value')
                        #     r_usage.hset(earliest_package_key, 'total_price', str(0.00))
                        #     total_price = 0.00
                        # r_usage.set(f"total_price:{user_id}:{prod_id}", str(total_price))
                        continue
                else:
                    count = int(earliest_package_info["count"])
                    if count <= 0:
                        # 令牌数不足，跳过当前流量包
                        continue

                # 如果未过期则跳出循环，开始使用流量包
                break
        else:
            # 如果所有流量包都已过期，返回错误信息
            code = RET.USED_UP
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message)

    @swagger_auto_schema(
        operation_id="120",
        tags=["v3.1"],
        operation_summary="通用流量包获取剩余费用",
        operation_description="获取用户通用流量包费用。",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="A success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="A success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            description="包含所有产品及其剩余令牌总数的列表。",
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
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
                            type=openapi.TYPE_INTEGER, description="An error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="An error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")

        r_usage = get_redis_connection("usage")
        r_config = get_redis_connection("config")
        ret_data = defaultdict(dict)
        universal_product_dict = r_config.get("config:products:universal")

        if isinstance(universal_product_dict, str):
            universal_product_dict = json.loads(universal_product_dict)

        all_prod_rest = 0
        for prod_name, prod_id in universal_product_dict.items():
            try:
                # 注意这里我们改用zrangebyscore函数，根据score（即order）进行排序
                package_keys = r_usage.zrangebyscore(
                    f"universal_packages:{user_id}:{prod_id}", "-inf", "+inf"
                )
                print(package_keys)
                earliest_expire_at = None
                for package_key in package_keys:
                    package_info = r_usage.hgetall(package_key)

                    if package_info:
                        rest_total_price = float(package_info["total_price"])
                        expire_at = float(package_info["expire_at"])

                        # 更新最早的过期时间
                        if earliest_expire_at is None or expire_at < earliest_expire_at:
                            earliest_expire_at = expire_at

                        # 检查是否已过期
                        if expire_at < datetime.datetime.now().timestamp():
                            # 已过期，从 Sorted Set 中删除
                            r_usage.zrem(
                                f"universal_packages:{user_id}:{prod_id}", package_key)
                            r_usage.decr(
                                f"total_price:{user_id}:{prod_id}",
                                rest_total_price)  # 更新用户的总剩余次数

                            # 释放空间, 已经过期的没必要再留着了, mysql 中有订单记录可以用作回溯
                            # r_usage.delete(package_key)
                            continue
            except Exception:
                print(traceback.format_exc())
            try:
                total_count = (
                        r_usage.get(f"total_price_origin:{user_id}:{prod_id}") or 0
                )
                try:
                    if Decimal(total_count) <= 0:
                        total_count = 0
                except Exception:
                    total_count = 0
                rest_count = r_usage.get(f"total_price:{user_id}:{prod_id}")
                try:
                    if Decimal(rest_count) <= 0:
                        rest_count = 0
                except Exception:
                    rest_count = 0
                # rest_count = r_usage.get(f"total_price:{user_id}:{prod_id}") or 0
                ret_data[prod_name]["rest"] = rest_count
                # ret_data[prod_name]['status'] = True if int(rest_count) > 0 else False
                ret_data[prod_name]["total"] = total_count
                all_prod_rest += float(rest_count)
            except Exception:
                print(traceback.format_exc())

        code = RET.OK
        message = Language.get(code)
        return CstResponse(
            code=code, message=message, total=all_prod_rest, data=[ret_data]
        )


class TrafficControlRouter(APIView):
    @swagger_auto_schema(
        operation_id="77",
        tags=["v3.1"],
        operation_summary="判断会员和流量包状态",
        operation_description="判断会员和流量包状态.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="用户ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Traffic control details for the user.",
                            properties={
                                "member": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="Member status and data.",
                                    properties={
                                        "status": openapi.Schema(
                                            type=openapi.TYPE_BOOLEAN,
                                            description="Member status",
                                        ),
                                        "data": openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            description="Member data",
                                        ),
                                    },
                                ),
                                "package": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="Package details with various traffic control packages.",
                                    properties={
                                        "gpt35": openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            description="gpt35 package details",
                                            properties={
                                                "status": openapi.Schema(
                                                    type=openapi.TYPE_BOOLEAN,
                                                    description="gpt35 package status",
                                                ),
                                                "data": openapi.Schema(
                                                    type=openapi.TYPE_INTEGER,
                                                    description="gpt35 package data",
                                                ),
                                            },
                                        ),
                                        "gpt40": openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            description="gpt40 package details",
                                            properties={
                                                "status": openapi.Schema(
                                                    type=openapi.TYPE_BOOLEAN,
                                                    description="gpt40 package status",
                                                ),
                                                "data": openapi.Schema(
                                                    type=openapi.TYPE_INTEGER,
                                                    description="gpt40 package data",
                                                ),
                                            },
                                        ),
                                        "baidu_drawing": openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            description="baidu_drawing package details",
                                            properties={
                                                "status": openapi.Schema(
                                                    type=openapi.TYPE_BOOLEAN,
                                                    description="baidu_drawing package status",
                                                ),
                                                "data": openapi.Schema(
                                                    type=openapi.TYPE_INTEGER,
                                                    description="baidu_drawing package data",
                                                ),
                                            },
                                        ),
                                        "dalle2": openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            description="dalle2 package details",
                                            properties={
                                                "status": openapi.Schema(
                                                    type=openapi.TYPE_BOOLEAN,
                                                    description="dalle2 package status",
                                                ),
                                                "data": openapi.Schema(
                                                    type=openapi.TYPE_INTEGER,
                                                    description="dalle2 package data",
                                                ),
                                            },
                                        ),
                                    },
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
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
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
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")
        user_type = request.query_params.get("user_type")

        request_data = {"user_id": user_id}
        try:
            member_info = requests.post(
                settings.SERVER_ADDRESS +
                "/pay/members_manage/",
                data=request_data)

            member_info_res = member_info.json()

            packages_info = requests.get(
                settings.SERVER_ADDRESS +
                "/pay/token_consume/",
                params=request_data)
            package_info_data = packages_info.json()

            packages_info_universal = requests.get(
                settings.SERVER_ADDRESS + "/pay/token_consume_universal/",
                params=request_data,
            )
            package_info_data_universal = packages_info_universal.json()

            ret_data = defaultdict(lambda: defaultdict(dict))
            if (
                    member_info_res.get("code") == 20000
                    and package_info_data.get("code") == 20000
                    and package_info_data_universal.get("code") == 20000
            ):
                member_info_data = member_info_res.get("data")
                package_info_data = package_info_data.get("data")

                if member_info_data:
                    member_info_expire = member_info_data[0].get("expire_date")

                    current_time = datetime.datetime.now()

                    member_info_expire = datetime.datetime.strptime(
                        member_info_expire, "%Y-%m-%d %H:%M:%S"
                    )

                    # 当前不是会员 或者会员过期
                    print("opoppopopopopopopopop")
                    if not member_info_data or current_time > member_info_expire:
                        ret_data["member"]["status"] = False
                        ret_data["member"]["data"]["count"] = {}

                    else:
                        ret_data["member"]["status"] = True
                        meber_rest_count = requests.get(
                            settings.SERVER_ADDRESS + "/pay/token_manage_redis/", params=request_data, )
                        meber_rest_count_data = meber_rest_count.json()

                        ret_data["member"]["data"] = member_info_data[0]
                        if meber_rest_count_data.get("code") == 20000:
                            ret_data["member"]["data"][
                                "count"
                            ] = meber_rest_count_data.get("data")
                        else:
                            ret_data["member"]["data"]["count"] = {}

                # 没有找到数据, 非会员
                else:
                    ret_data["member"]["status"] = False

                    request_data["user_type"] = user_type

                    member_rest_count = requests.get(
                        settings.SERVER_ADDRESS +
                        "/pay/token_manage_redis_no_vip/",
                        params=request_data,
                    )
                    member_rest_count_data = member_rest_count.json()

                    if member_rest_count_data.get("code") == 20000:
                        ret_data["member"]["data"][
                            "count"
                        ] = member_rest_count_data.get("data")
                    else:
                        ret_data["member"]["data"] = {}

                package_data = defaultdict(lambda: defaultdict(dict))
                if package_info_data:
                    gpt35 = package_info_data[0].get("gpt35")
                    gpt40 = package_info_data[0].get("gpt40")
                    dalle2 = package_info_data[0].get("dalle2")
                    baidu_drawing = package_info_data[0].get("baidu_drawing")
                    wenxin = package_info_data[0].get("wenxin")
                    xunfei = package_info_data[0].get("xunfei")
                    mj = package_info_data[0].get("mj")
                    claude = package_info_data[0].get("claude")
                    chatglm = package_info_data[0].get("chatglm")
                    stabel_diffusion = package_info_data[0].get(
                        "stablediffusion")
                    qianwen = package_info_data[0].get("qianwen")
                    sensecore = package_info_data[0].get("sensecore")
                    ai_360 = package_info_data[0].get("360")

                    package_data["package"]["gpt35"]["status"] = (
                        True if int(gpt35.get("rest")) > 0 else False
                    )
                    package_data["package"]["gpt35"]["value"] = (
                        int(gpt35.get("rest")) if int(gpt35.get("rest")) > 0 else 0
                    )
                    package_data["package"]["gpt40"]["status"] = (
                        True if int(gpt40.get("rest")) > 0 else False
                    )
                    package_data["package"]["gpt40"]["value"] = (
                        int(gpt40.get("rest")) if int(gpt40.get("rest")) > 0 else 0
                    )
                    package_data["package"]["dalle2"]["status"] = (
                        True if int(dalle2.get("rest")) > 0 else False
                    )
                    package_data["package"]["dalle2"]["value"] = (
                        int(dalle2.get("rest")) if int(dalle2.get("rest")) > 0 else 0
                    )
                    package_data["package"]["baidu_drawing"]["status"] = (
                        True if int(baidu_drawing.get("rest")) > 0 else False
                    )
                    package_data["package"]["baidu_drawing"]["value"] = (
                        int(baidu_drawing.get("rest"))
                        if int(baidu_drawing.get("rest")) > 0
                        else 0
                    )

                    package_data["package"]["wenxin"]["status"] = (
                        True if int(wenxin.get("rest")) > 0 else False
                    )
                    package_data["package"]["wenxin"]["value"] = (
                        int(wenxin.get("rest")) if int(wenxin.get("rest")) > 0 else 0
                    )

                    package_data["package"]["claude"]["status"] = (
                        True if int(claude.get("rest")) > 0 else False
                    )
                    package_data["package"]["claude"]["value"] = (
                        int(claude.get("rest")) if int(claude.get("rest")) > 0 else 0
                    )
                    package_data["package"]["chatglm"]["status"] = (
                        True if int(chatglm.get("rest")) > 0 else False
                    )
                    package_data["package"]["chatglm"]["value"] = (
                        int(chatglm.get("rest")) if int(chatglm.get("rest")) > 0 else 0
                    )

                    package_data["package"]["xunfei"]["status"] = (
                        True if int(xunfei.get("rest")) > 0 else False
                    )
                    package_data["package"]["xunfei"]["value"] = (
                        int(xunfei.get("rest")) if int(xunfei.get("rest")) > 0 else 0
                    )

                    package_data["package"]["mj"]["status"] = (
                        True if int(mj.get("rest")) > 0 else False
                    )
                    package_data["package"]["mj"]["value"] = (
                        int(mj.get("rest")) if int(mj.get("rest")) > 0 else 0
                    )

                    package_data["package"]["stablediffusion"]["status"] = (
                        True if int(stabel_diffusion.get("rest")) > 0 else False
                    )
                    package_data["package"]["stablediffusion"]["value"] = (
                        int(mj.get("rest"))
                        if int(stabel_diffusion.get("rest")) > 0
                        else 0
                    )

                    package_data["package"]["qianwen"]["status"] = (
                        True if int(qianwen.get("rest")) > 0 else False
                    )
                    package_data["package"]["qianwen"]["value"] = (
                        int(qianwen.get("rest")) if int(qianwen.get("rest")) > 0 else 0
                    )

                    package_data["package"]["sensecore"]["value"] = (
                        int(sensecore.get("rest"))
                        if int(sensecore.get("rest")) > 0
                        else 0
                    )
                    package_data["package"]["sensecore"]["status"] = (
                        True if int(sensecore.get("rest")) > 0 else False
                    )
                    print(ai_360)
                    package_data["package"]["360"]["value"] = (
                        int(ai_360.get("rest")) if int(ai_360.get("rest")) > 0 else 0
                    )
                    package_data["package"]["360"]["status"] = (
                        True if int(ai_360.get("rest")) > 0 else False
                    )
                else:
                    package_data["package"]["gpt35"]["status"] = False
                    package_data["package"]["gpt35"]["value"] = 0
                    package_data["package"]["gpt40"]["status"] = False
                    package_data["package"]["gpt40"]["value"] = 0
                    package_data["package"]["dalle2"]["status"] = False
                    package_data["package"]["dalle2"]["value"] = 0
                    package_data["package"]["baidu_drawing"]["status"] = False
                    package_data["package"]["baidu_drawing"]["value"] = 0

                    package_data["package"]["wenxin"]["status"] = False
                    package_data["package"]["wenxin"]["value"] = 0

                    package_data["package"]["claude"]["status"] = False
                    package_data["package"]["claude"]["value"] = 0
                    package_data["package"]["chatglm"]["status"] = False
                    package_data["package"]["chatglm"]["value"] = 0

                    package_data["package"]["xunfei"]["status"] = False
                    package_data["package"]["xunfei"]["value"] = 0

                    package_data["package"]["mj"]["status"] = False
                    package_data["package"]["mj"]["value"] = 0

                    package_data["package"]["stablediffusion"]["status"] = False
                    package_data["package"]["stablediffusion"]["value"] = 0

                    package_data["package"]["qianwen"]["status"] = False
                    package_data["package"]["qianwen"]["value"] = 0

                    package_data["package"]["sensecore"]["status"] = False
                    package_data["package"]["sensecore"]["value"] = 0
                    package_data["package"]["360"]["value"] = 0

                if package_info_data_universal:
                    package_data["package"]["universal"]["total"] = float(
                        package_info_data_universal.get("total")
                    )
                    packages_info_universal_data = package_info_data_universal.get(
                        "data"
                    )[0]
                    package_data["package"]["universal"][
                        "universal"
                    ] = packages_info_universal_data.get("universal")
                    package_data["package"]["universal"][
                        "universal_9"
                    ] = packages_info_universal_data.get("universal_9")
                    package_data["package"]["universal"][
                        "universal_8"
                    ] = packages_info_universal_data.get("universal_8")
                    package_data["package"]["universal"][
                        "universal_5"
                    ] = packages_info_universal_data.get("universal_5")
                    package_data["package"]["universal"][
                        "universal_hidden_2"
                    ] = packages_info_universal_data.get("universal_hidden_2")
                    package_data["package"]["universal"][
                        "universal_hidden_10"
                    ] = packages_info_universal_data.get("universal_hidden_10")
                else:
                    package_data["package"]["universal"]["total"] = 0.00
                    package_data["package"]["universal"]["universal"] = 0.00
                    package_data["package"]["universal"]["universal_9"] = 0.00
                    package_data["package"]["universal"]["universal_8"] = 0.00
                    package_data["package"]["universal"]["universal_5"] = 0.00
                    package_data["package"]["universal"]["universal_hidden_2"] = 0.00
                    package_data["package"]["universal"]["universal_hidden_10"] = 0.00
                ret_data.update(package_data)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
            else:
                code = RET.NETWORK_ERROR
                message = Language.get(code)

                return CstResponse(code=code, message=message)
        except Exception as e:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)

            return CstResponse(code=code, message=message)


class OmtMessageCenterManage(APIView):
    def __init__(self):
        super(OmtMessageCenterManage, self).__init__()

    @swagger_auto_schema(
        operation_id="变更已读",
        tags=["消息中心"],
        operation_summary="变更已读",
        operation_description="变更消息状态为已读状态.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "message_ids"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="user_id."
                ),
                "message_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="message_id, 为数组.",
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully marked the messages as read.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def put(self, request):

        data = request.data
        message_ids = data.get("message_ids")
        user_id = data.get("user_id")
        if not user_id:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

        if message_ids:
            message_ids = set(message_ids)

            # Convert message_ids set to list of VALUES strings
            values_str_list = [
                f"({user_id}, {message_id}, 1)" for message_id in message_ids
            ]
            values_str = ", ".join(values_str_list)

            if not values_str:
                sql_update_read = False
            else:
                # Generate SQL statement
                sql_update_read = f"INSERT INTO  {settings.ADMIN_DB}.omt_message_read_status (user_id, message_id, is_read) VALUES {values_str}"
        else:
            sql_get_user_unread_message = f"""
                    SELECT m.message_id
                    FROM {settings.ADMIN_DB}.omt_message_center AS m
                    LEFT JOIN {settings.ADMIN_DB}.omt_message_read_status AS r
                    ON m.message_id = r.message_id AND r.user_id = {user_id}
                    WHERE r.message_id IS NULL
            """

            # 如果没有提供message_ids，那么需要查找用户的所有未读消息
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_user_unread_message)
                unread_data = MysqlOper.get_query_result(cursor)
                message_ids = [each.get("message_id") for each in unread_data]
                message_ids = set(message_ids)

                # Convert message_ids set to list of VALUES strings
                values_str_list = [
                    f"({user_id}, {message_id}, 1)" for message_id in message_ids]
                values_str = ", ".join(values_str_list)

                if not values_str:
                    sql_update_read = False
                else:
                    # Generate SQL statement
                    sql_update_read = f"INSERT INTO  {settings.ADMIN_DB}.omt_message_read_status (user_id, message_id, is_read) VALUES {values_str}"

        logger.info(sql_update_read)

        if not sql_update_read:
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message)

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_update_read)
                rowcount = cursor.rowcount
                if len(message_ids) == rowcount:
                    code = RET.OK
                    message = Language.get(code)
                    return CstResponse(code=code, message=message)
                else:
                    code = RET.NETWORK_ERROR
                    message = Language.get(code)
                    raise CstException(code=code, message=message)
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)

    @swagger_auto_schema(
        operation_id="获取消息列表",
        tags=["V5.5"],
        operation_summary="获取消息列表",
        operation_description="获取消息列表.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "message_type"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="user_id."
                ),
                "message_type": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="消息类型， 默认传2."
                ),
                "page_index": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="页码."
                ),
                "page_count": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="页数."
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched the messages.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="The list of messages.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "message_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="消息id. V5.5",
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="标题. V5.5"
                                    ),
                                    "desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="描述."
                                    ),
                                    "start_time": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format=openapi.FORMAT_DATETIME,
                                        description="开始时间.",
                                    ),
                                    "end_time": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format=openapi.FORMAT_DATETIME,
                                        description="结束时间.",
                                    ),
                                    "target_type": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="目标类型."
                                    ),
                                    "message_type": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="消息类型. 详情查看文档相关 MESSAGE_STATUS.  V5.5",
                                    ),
                                    "image": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="首页图片."
                                    ),
                                    "like_count": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="点赞量. V5.5",
                                    ),
                                    "read_count": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="阅读量. V5.5",
                                    ),
                                    "is_arousel": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN,
                                        description="是否轮播 0 否 1 是.",
                                    ),
                                    "status": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="消息状态 详情查看文档相关 MESSAGE_STATUS.",
                                    ),
                                    "is_read": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN,
                                        description="已读状态 0 未读 1：已读.",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")
        is_arousel = data.get("is_arousel")
        page_index = data.get("page_index")
        page_count = data.get("page_count")
        message_type = data.get("message_type", 0)
        cate = data.get('cate')
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if int(message_type) != 2:
            sql_get_messages = f"""
                        SELECT m.id, m.message_id, m.title, m.content,m.cate, m.desc, m.start_time, m.end_time,
                         m.target_type, m.message_type, m.is_arousel, m.status, m.create_time, m.update_time,
                        IF(r.message_id IS NULL, 0, 1) AS is_read
                        FROM {settings.ADMIN_DB}.omt_message_center AS m
                        LEFT JOIN {settings.ADMIN_DB}.omt_message_read_status AS r
                        ON m.message_id = r.message_id AND r.user_id = {user_id}
                        WHERE m.start_time <= '{current_date}' AND m.status = '1' AND m.message_type = {message_type} """
            sql_get_messages_raw = f"""
                                SELECT COUNT(DISTINCT(m.message_id)) AS total
                                FROM {settings.ADMIN_DB}.omt_message_center AS m
                                LEFT JOIN {settings.ADMIN_DB}.omt_message_read_status AS r
                                ON m.message_id = r.message_id AND r.user_id = {user_id}
                                WHERE m.start_time <= '{current_date}' AND m.status = '1' AND m.message_type = {message_type} """
            if is_arousel:
                sql_get_messages += f" AND is_arousel = {str(is_arousel)} "
        else:
            sql_get_messages = f"""
                                    SELECT m.id, m.message_id, m.title, m.content, m.desc,m.cate, m.start_time, 
                                    m.message_type,  m.status,m.image, m.like_count, m.read_count, m.create_time, m.update_time
                                    FROM {settings.ADMIN_DB}.omt_message_center AS m
                                    WHERE m.start_time <= '{current_date}' AND m.status = '1' AND m.message_type = {message_type} """
            sql_get_messages_raw = f"""
                                            SELECT COUNT(DISTINCT(m.message_id)) AS total
                                            FROM {settings.ADMIN_DB}.omt_message_center AS m
                                            WHERE m.start_time <= '{current_date}' AND m.status = '1' AND m.message_type = {message_type} """

        if cate is not None:
            sql_get_messages += f" AND cate = '{cate}' "
            sql_get_messages_raw += f" AND cate = '{cate}' "

        sql_get_messages += " ORDER BY m.weight DESC, m.create_time DESC"

        if page_count is not None:
            sql_get_messages += " LIMIT " + str(page_count)

            if page_index is not None:
                row_index = int(int(page_index) - 1) * int(page_count)
                sql_get_messages += " OFFSET " + str(row_index)

        logger.info(sql_get_messages)

        ret_data = []

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_messages_raw)
                query_total_data = MysqlOper.get_query_result(cursor)
                query_total = query_total_data[0].get("total")
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_messages)
                query_data = MysqlOper.get_query_result(cursor)
                for each_message in query_data:
                    dict_each_message = {}
                    message_id = each_message.get("message_id")
                    title = each_message.get("title")
                    desc = each_message.get("desc", "")
                    cate = each_message.get("cate", "")
                    start_time = each_message.get("start_time", "")
                    end_time = each_message.get("end_time", "")
                    target_type = each_message.get("target_type", "")
                    message_type = each_message.get("message_type", "")
                    is_arousel = each_message.get("is_arousel", "")
                    status = each_message.get("status", "")
                    is_read = each_message.get("is_read", "")
                    image = each_message.get("image", "")
                    like_count = each_message.get("like_count", 0)
                    read_count = each_message.get("read_count", 0)

                    dict_each_message["message_id"] = message_id
                    dict_each_message["title"] = title
                    dict_each_message["image"] = image
                    dict_each_message["like_count"] = like_count
                    dict_each_message["read_count"] = read_count
                    dict_each_message["desc"] = desc
                    dict_each_message["cate"] = cate
                    dict_each_message["start_time"] = start_time
                    dict_each_message["end_time"] = end_time
                    dict_each_message["target_type"] = target_type
                    dict_each_message["message_type"] = message_type
                    dict_each_message["is_arousel"] = is_arousel
                    dict_each_message["status"] = status
                    dict_each_message["is_read"] = is_read
                    dict_each_message["create_time"] = start_time

                    ret_data.append(dict_each_message)

            code = RET.OK
            message = Language.get(code)
            return CstResponse(
                code=code, message=message, data=ret_data, total=query_total
            )
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class OmtMessageCenterContentManage(APIView):
    def __init__(self):
        super(OmtMessageCenterContentManage, self).__init__()

    @swagger_auto_schema(
        operation_id="获取消息详情",
        tags=["V5.5"],
        operation_summary="获取详情",
        operation_description="获取消息详情",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "message_type", "message_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="user id."
                ),
                "message_type": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="消息类型， 默认传2"
                ),
                "message_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="message id."
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched the message.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="The message.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "message_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER,
                                        description="message id.",
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="标题."
                                    ),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="内容."
                                    ),
                                    "desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="简介."
                                    ),
                                    "is_arousel": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN, description="是否轮播."
                                    ),
                                    "is_read": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN, description="已读状态."
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):

        data = request.data

        user_id = data.get("user_id")
        message_id = data.get("message_id")

        # First, mark the message as read by inserting a new record
        sql_mark_as_read = f"""
                INSERT INTO omt_message_read_status (message_id, user_id, is_read)
                VALUES ({message_id}, {user_id}, 1)
                ON DUPLICATE KEY UPDATE is_read = 1"""

        logger.info(sql_mark_as_read)

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_mark_as_read)

        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)

        # Then, fetch the message
        sql_get_messages = (
            f"SELECT  m.message_id, m.title, m.content, m.desc, m.start_time, m.is_arousel, m.create_time, 1 AS is_read,"
            f" m.like_count, m.read_count "
            f" FROM {settings.ADMIN_DB}.omt_message_center AS m WHERE m.message_id = {message_id} " )

        logger.info(sql_get_messages)

        ret_data = []

        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_messages)
                query_data = MysqlOper.get_query_result(cursor)
                for each_message in query_data:
                    dict_each_message = {}
                    message_id = each_message.get("message_id")
                    title = each_message.get("title")
                    content = each_message.get("content")
                    desc = each_message.get("desc")
                    is_arousel = each_message.get("is_arousel")
                    is_read = each_message.get("is_read")
                    read_count = each_message.get("read_count")
                    create_time = each_message.get("start_time")
                    # 阅读数破 1W 后增长有点太骗人了
                    if int(read_count) > 10000:
                        read_count = int(
                            int(read_count)
                            + (int(read_count) * random.uniform(0.01, 0.02))
                        )
                    else:
                        read_count = int(
                            int(read_count)
                            + (int(read_count) * random.uniform(0.1, 0.3))
                        )
                    like_count = int(read_count * random.uniform(0.2, 0.5))

                    sql_update_forge_read_like = (
                        f"UPDATE {settings.ADMIN_DB}.omt_message_center SET read_count = {read_count},  "
                        f"like_count = {like_count} WHERE message_id = {message_id}")

                    try:
                        with connections[settings.ADMIN_DB].cursor() as cursor:
                            cursor.execute(sql_update_forge_read_like)
                            if not cursor.rowcount > 0:
                                code = RET.DB_ERR
                                message = Language.get(code)
                                return CstResponse(code=code, message=message)
                    except Exception:
                        code = RET.DB_ERR
                        message = Language.get(code)
                        raise CstException(code=code, message=message)
                    dict_each_message["message_id"] = message_id
                    dict_each_message["title"] = title
                    dict_each_message["content"] = content
                    dict_each_message["desc"] = desc
                    dict_each_message["is_arousel"] = is_arousel
                    dict_each_message["is_read"] = is_read
                    dict_each_message["like_count"] = like_count
                    dict_each_message["read_count"] = read_count
                    dict_each_message["create_time"] = create_time

                    ret_data.append(dict_each_message)

            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            print(traceback.format_exc())
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            raise CstException(code=code, message=message)


# 旧版计费中心，暂时废弃
# class BillingCenter(APIView):
#     @swagger_auto_schema(
#         operation_id='计费中心',
#         tags=['v3.2'],
#         operation_summary='计费中心',
#         operation_description='根据用户ID查询订单，查询结果按创建时间倒序，限制5条',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['user_id'],
#             properties={
#                 'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='user id.')
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Successfully fetched the orders.',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Success code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message.'),
#                         'data': openapi.Schema(
#                             type=openapi.TYPE_OBJECT,
#                             description='The orders.',
#                             additional_properties=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     'prod_name': openapi.Schema(type=openapi.TYPE_STRING, description='商品名称.'),
#                                     'prod_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='商品ID.'),
#                                     'prod_cate_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='商品种类ID.'),
#                                     'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='总额.'),
#                                     'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='订单创建时间.'),
#                                     'points': openapi.Schema(type=openapi.TYPE_INTEGER, description='总积分.'),
#                                     'packages_rest': openapi.Schema(
#                                         type=openapi.TYPE_OBJECT,
#                                         properties={
#                                             'AI35': openapi.Schema(type=openapi.TYPE_STRING, description='AI35.'),
#                                             'AI40': openapi.Schema(type=openapi.TYPE_STRING, description='AI40.'),
#                                             'DALLE2': openapi.Schema(type=openapi.TYPE_STRING, description='DALLE2.'),
#                                             'baidu_drawing': openapi.Schema(type=openapi.TYPE_STRING,
#                                                                             description='百度绘画.'),
#                                             'wenxin': openapi.Schema(type=openapi.TYPE_STRING, description='文心一言.'),
#                                             'xunfei': openapi.Schema(type=openapi.TYPE_STRING, description='讯飞星火.'),
#                                             'mj': openapi.Schema(type=openapi.TYPE_STRING, description='Midjourney.'),
#
#                                         },
#                                         description='剩余积分.'),
#                                 }
#                             )
#                         )
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Server error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message.'),
#                     }
#                 )
#             )
#         }
#     )
#     def post(self, request):
#         r_usage = get_redis_connection('usage')
#         user_id = request.data.get('user_id')
#
#         sql_fetch_orders = f"""
#                   SELECT a.order_id, b.prod_name, b.prod_id, b.prod_cate_id,b.prod_origin_price,  a.total_amount, a.created_at
#                   FROM {settings.DEFAULT_DB}.po_orders AS a
#                   LEFT JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON a.order_id = oi.order_id
#                   LEFT JOIN {settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id
#                   WHERE a.is_delete = 0 AND a.user_id = {user_id} AND oi.is_delete = 0 AND a.status = 2
#                   AND a.prod_cate_id not in (4, 3) ORDER BY a.created_at DESC
#             """
#
#         logger.error(sql_fetch_orders)
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute(sql_fetch_orders)
#                 query_data = MysqlOper.get_query_result(cursor)
#                 ret_data = defaultdict(list)
#
#                 packages_rest = defaultdict(dict)
#
#                 for each_data in query_data:
#                     each_data_dict = {}
#
#                     prod_name = each_data.get('prod_name')
#                     order_id = each_data.get('order_id')
#                     prod_id = each_data.get('prod_id')
#                     prod_cate_id = each_data.get('prod_cate_id')
#                     prod_origin_price = each_data.get('prod_origin_price')
#                     total_amount = each_data.get('total_amount')
#                     created_at = each_data.get('created_at')
#                     points = str(math.ceil(float(prod_origin_price) * settings.POINTS_UNIT))
#
#                     each_data_dict['order_id'] = order_id
#                     each_data_dict['prod_name'] = prod_name
#                     each_data_dict['prod_id'] = prod_id
#                     each_data_dict['prod_cate_id'] = prod_cate_id
#                     each_data_dict['total_amount'] = total_amount
#                     each_data_dict['created_at'] = created_at
#                     each_data_dict['points'] = points
#
#                     if int(prod_cate_id) == 5:
#                         rest_points = gadgets.user_rest_value_redis(prod_id, user_id, prod_cate_id, r_usage)
#                         each_data_dict['rest_points'] = rest_points
#                         packages_rest[settings.PROD_ID_NAME_MAP.get(int(prod_id))[1]] = int(rest_points)
#
#                     if prod_cate_id in ret_data.keys():
#                         ret_data[prod_cate_id].append(each_data_dict)
#                     else:
#                         ret_data[prod_cate_id] = [each_data_dict]
#
#                 request_data = {
#                     'user_id': user_id
#                 }
#                 packages_info_universal = requests.get(
#                     settings.SERVER_ADDRESS + '/pay/token_consume_universal/',
#                     params=request_data)
#
#                 packages_info_universal_data = packages_info_universal.json()
#                 universal_rest = packages_info_universal_data.get('total')
#                 ret_data['packages_rest'] = packages_rest
#                 ret_data['universal_rest'] = int(universal_rest)
#
#                 code = RET.OK
#                 message = Language.get(code)
#                 return CstResponse(code=code, message=message, data=ret_data)
#         except Exception:
#             code = RET.NETWORK_ERROR
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)
#
#     @swagger_auto_schema(
#         operation_id='获取定价规则',
#         tags=['v3.2'],
#         operation_summary='获取定价规则',
#         operation_description='获取定价规则',
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Successfully fetched the pricing rule.',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Success code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message.'),
#                         'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='Pricing rule data.'),
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Server error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message.'),
#                     }
#                 )
#             )
#         }
#     )
#     def get(self, request):
#         r = get_redis_connection('config')
#         pricing_rule = r.get('config:pricing')
#         try:
#             pricing_rule = json.loads(pricing_rule)
#         except Exception:
#             code = RET.NETWORK_ERROR
#             message = Language.get(code)
#             return CstResponse(code=code, message=message, data=pricing_rule)
#
#         code = RET.OK
#         message = Language.get(code)
#         return CstResponse(code=code, message=message, data=pricing_rule)

# class BillingCenter(APIView):
#     @swagger_auto_schema(
#         operation_id='计费中心',
#         tags=['v3.2'],
#         operation_summary='计费中心',
#         operation_description='根据用户ID查询订单，查询结果按创建时间倒序，限制5条',
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['user_id'],
#             properties={
#                 'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='user id.')
#             }
#         ),
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Successfully fetched the orders.',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Success code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message.'),
#                         'data': openapi.Schema(
#                             type=openapi.TYPE_OBJECT,
#                             description='The orders.',
#                             additional_properties=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     'prod_name': openapi.Schema(type=openapi.TYPE_STRING, description='商品名称.'),
#                                     'prod_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='商品ID.'),
#                                     'prod_cate_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='商品种类ID.'),
#                                     'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='总额.'),
#                                     'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='订单创建时间.'),
#                                     'points': openapi.Schema(type=openapi.TYPE_INTEGER, description='总积分.'),
#                                     'packages_rest': openapi.Schema(
#                                         type=openapi.TYPE_OBJECT,
#                                         properties={
#                                             'AI35': openapi.Schema(type=openapi.TYPE_STRING, description='AI35.'),
#                                             'AI40': openapi.Schema(type=openapi.TYPE_STRING, description='AI40.'),
#                                             'DALLE2': openapi.Schema(type=openapi.TYPE_STRING, description='DALLE2.'),
#                                             'baidu_drawing': openapi.Schema(type=openapi.TYPE_STRING,
#                                                                             description='百度绘画.'),
#                                             'wenxin': openapi.Schema(type=openapi.TYPE_STRING, description='文心一言.'),
#                                             'xunfei': openapi.Schema(type=openapi.TYPE_STRING, description='讯飞星火.'),
#                                             'mj': openapi.Schema(type=openapi.TYPE_STRING, description='Midjourney.'),
#
#                                         },
#                                         description='剩余积分.'),
#                                 }
#                             )
#                         )
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Server error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message.'),
#                     }
#                 )
#             )
#         }
#     )
#     def post(self, request):
#         user_id = request.data.get('user_id')
#
#         sql_fetch_orders = f"""
#                   SELECT a.order_id, b.prod_name, b.prod_id, b.prod_cate_id,b.prod_origin_price,  a.total_amount, a.created_at
#                   FROM {settings.DEFAULT_DB}.po_orders AS a
#                   LEFT JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON a.order_id = oi.order_id
#                   LEFT JOIN {settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id
#                   WHERE a.is_delete = 0 AND a.user_id = {user_id} AND oi.is_delete = 0 AND a.status = 2
#                   AND a.prod_cate_id not in (4, 3) ORDER BY a.created_at DESC
#             """
#
#         logger.error(sql_fetch_orders)
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute(sql_fetch_orders)
#                 query_data = MysqlOper.get_query_result(cursor)
#                 ret_data = defaultdict(list)
#
#                 packages_rest = defaultdict(dict)
#
#                 for each_data in query_data:
#                     each_data_dict = {}
#
#                     prod_name = each_data.get('prod_name')
#                     order_id = each_data.get('order_id')
#                     prod_id = each_data.get('prod_id')
#                     prod_cate_id = each_data.get('prod_cate_id')
#                     prod_origin_price = each_data.get('prod_origin_price')
#                     total_amount = each_data.get('total_amount')
#                     created_at = each_data.get('created_at')
#                     points = str(math.ceil(float(prod_origin_price) * settings.POINTS_UNIT))
#
#                     each_data_dict['order_id'] = order_id
#                     each_data_dict['prod_name'] = prod_name
#                     each_data_dict['prod_id'] = prod_id
#                     each_data_dict['prod_cate_id'] = prod_cate_id
#                     each_data_dict['total_amount'] = total_amount
#                     each_data_dict['created_at'] = created_at
#                     each_data_dict['points'] = points
#
#                     if prod_cate_id in ret_data.keys():
#                         ret_data[prod_cate_id].append(each_data_dict)
#                     else:
#                         ret_data[prod_cate_id] = [each_data_dict]
#
#                 request_data = {
#                     'user_id': user_id
#                 }
#                 packages_info_universal = requests.get(
#                     settings.SERVER_ADDRESS + '/pay/token_consume_universal/',
#                     params=request_data)
#
#                 packages_info_universal_data = packages_info_universal.json()
#                 universal_rest = packages_info_universal_data.get('total')
#                 ret_data['packages_rest'] = packages_rest
#                 ret_data['universal_rest'] = int(universal_rest)
#
#                 code = RET.OK
#                 message = Language.get(code)
#                 return CstResponse(code=code, message=message, data=ret_data)
#         except Exception:
#             code = RET.NETWORK_ERROR
#             message = Language.get(code)
#             trace = str(traceback.format_exc())
#             logger.error(trace)
#             raise CstException(code=code, message=message)
#
#     @swagger_auto_schema(
#         operation_id='获取定价规则',
#         tags=['v3.2'],
#         operation_summary='获取定价规则',
#         operation_description='获取定价规则',
#         responses={
#             status.HTTP_200_OK: openapi.Response(
#                 description='Successfully fetched the pricing rule.',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Success code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message.'),
#                         'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='Pricing rule data.'),
#                     }
#                 )
#             ),
#             status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
#                 description='Server error',
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Error code.'),
#                         'message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message.'),
#                     }
#                 )
#             )
#         }
#     )
#     def get(self, request):
#         r = get_redis_connection('config')
#         pricing_rule = r.get('config:pricing')
#         try:
#             pricing_rule = json.loads(pricing_rule)
#         except Exception:
#             code = RET.NETWORK_ERROR
#             message = Language.get(code)
#             return CstResponse(code=code, message=message, data=pricing_rule)
#
#         code = RET.OK
#         message = Language.get(code)
#         return CstResponse(code=code, message=message, data=pricing_rule)


class BillingCenter(APIView):
    @swagger_auto_schema(
        operation_id="计费中心",
        tags=["v3.2"],
        operation_summary="计费中心",
        operation_description="根据用户ID查询订单，查询结果按创建时间倒序，限制5条",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="user id."
                )
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched the orders.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="The orders.",
                            additional_properties=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "prod_name": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="商品名称."
                                    ),
                                    "prod_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="商品ID."
                                    ),
                                    "prod_cate_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="商品种类ID."
                                    ),
                                    "total_amount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER, description="总额."
                                    ),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="订单创建时间."
                                    ),
                                    "points": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="总积分."
                                    ),
                                    "packages_rest": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "AI35": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="AI35.",
                                            ),
                                            "AI40": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="AI40.",
                                            ),
                                            "DALLE2": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="DALLE2.",
                                            ),
                                            "baidu_drawing": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="百度绘画.",
                                            ),
                                            "wenxin": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="文心一言.",
                                            ),
                                            "xunfei": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="讯飞星火.",
                                            ),
                                            "mj": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                description="Midjourney.",
                                            ),
                                        },
                                        description="剩余积分.",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    # 2023.11.15新增内容, ret_data[9] 系统赠送通用算力包记录, demo {'created_at': '2023-11-15 14:34:58', 'hash_rates': 50,
    # 'reason': '邀请好友注册赠送', 'expire_at': '2024-11-14 14:34:58'}:
    def post(self, request):
        user_id = request.data.get("user_id")

        sql_fetch_orders = f"""
                  SELECT a.order_id, b.prod_name, b.prod_id, b.prod_cate_id,b.hashrate,b.valid_period_days, b.prod_origin_price,  a.total_amount, a.created_at
                  FROM {settings.DEFAULT_DB}.po_orders AS a
                  LEFT JOIN {settings.DEFAULT_DB}.po_orders_items AS oi ON a.order_id = oi.order_id
                  LEFT JOIN {settings.DEFAULT_DB}.pp_products AS b ON oi.prod_id = b.prod_id
                  WHERE a.is_delete = 0 AND a.user_id = {user_id} AND oi.is_delete = 0 AND a.status = 2
                  AND a.prod_cate_id in (3, 6) ORDER BY a.created_at DESC
            """

        logger.error(sql_fetch_orders)

        ret_data = defaultdict(list)

        complimentary = gadgets.summarize_complimentary_hash_rates(user_id)

        ret_data[9] = complimentary

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_fetch_orders)
                query_data = MysqlOper.get_query_result(cursor)

                for each_data in query_data:
                    each_data_dict = {}

                    prod_name = each_data.get("prod_name")
                    order_id = each_data.get("order_id")
                    prod_id = each_data.get("prod_id")
                    prod_cate_id = each_data.get("prod_cate_id")
                    valid_period_days = each_data.get("valid_period_days")
                    total_amount = each_data.get("total_amount")
                    created_at = each_data.get("created_at")
                    points = each_data.get("hashrate")
                    from datetime import datetime, timedelta

                    expire_at = datetime.strptime(
                        created_at, "%Y-%m-%d %H:%M:%S")
                    expire_at += timedelta(days=int(valid_period_days))
                    expire_at = expire_at.strftime("%Y-%m-%d %H:%M:%S")

                    each_data_dict["order_id"] = order_id
                    each_data_dict["prod_name"] = prod_name
                    each_data_dict["prod_id"] = prod_id
                    each_data_dict["prod_cate_id"] = prod_cate_id
                    each_data_dict["total_amount"] = total_amount
                    each_data_dict["points"] = points
                    each_data_dict["created_at"] = created_at
                    each_data_dict["expire_at"] = expire_at

                    if prod_cate_id in ret_data.keys():
                        ret_data[prod_cate_id].append(each_data_dict)
                    else:
                        ret_data[prod_cate_id] = [each_data_dict]

                url = (
                        settings.SERVER_BILL_URL
                        + ":"
                        + settings.SERVER_BILL_PORT
                        + settings.HASHRATE_ADDRESS
                        + f"/{user_id}"
                )
                get_hashrate_req = requests.get(url=url)

                if get_hashrate_req.status_code == 200:
                    get_hashrate_data = json.loads(get_hashrate_req.text)
                    if get_hashrate_data.get("code") == 20000:
                        get_hashrate_data = get_hashrate_data["data"]
                        hash_rates = get_hashrate_data.get("hash_rates")
                        hash_rate_rules = get_hashrate_data.get("rules")

                ret_data["hash_rates"] = hash_rates
                ret_data["rules"] = hash_rate_rules

                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            trace = str(traceback.format_exc())
            logger.error(trace)
            raise CstException(code=code, message=message)


class QeustionSetRecommend(APIView):
    @swagger_auto_schema(
        operation_id="获取推荐问题集",
        tags=["v3.2"],
        operation_summary="获取推荐问题集",
        operation_description="随机从各模块中获取推荐问题集",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched the recommended question sets.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="The recommended question sets.",
                            additional_properties=openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "question_id": openapi.Schema(
                                            type=openapi.TYPE_INTEGER,
                                            description="问题集ID.",
                                        ),
                                        "title": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="问题集标题.",
                                        ),
                                        "content": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="问题集内容.",
                                        ),
                                        "module_name": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="模块名称 name.",
                                        ),
                                    },
                                ),
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        r = get_redis_connection("questions")

        module_names = r.keys('*')  # 假设所有模块名都在 Redis 的 32号数据库中

        # 随机选择三个模块
        selected_modules = random.sample(module_names, 3)

        # 从每个选中的模块中获取三个问题
        output_data = {}
        for idx, module in enumerate(selected_modules):
            # 获取当前模块的所有问题
            all_questions = r.hgetall(module)

            # 随机选择三个问题
            selected_questions = random.sample(list(all_questions.values()), 3)

            # 解析问题数据并添加到输出中
            output_data[str(idx)] = [json.loads(question) for question in selected_questions]

        code = RET.OK
        message = Language.get(code)
        return CstResponse(code=code, message=message, data=output_data)


class DrawingSetRecommend(APIView):
    @swagger_auto_schema(
        operation_id="获取推荐画集",
        tags=["v3.2"],
        operation_summary="获取推荐画集",
        operation_description="随机获取推荐画集",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully fetched the recommended drawings.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Success code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Success message."
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "pic_id": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="图片id."
                                    ),
                                    "pic_desc": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片描述."
                                    ),
                                    "pic_url": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="图片地址."
                                    ),
                                },
                            ),
                            description="The recommended drawings.",
                        ),
                        "total": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Total number of recommended drawings.",
                        ),
                    },
                ),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Error code."
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message."
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):

        sql_get_random_drawing = (
            f"SELECT pic_id, pic_desc, pic_url FROM {settings.DEFAULT_DB}.op_pictures "
            f"WHERE type = 5")

        logger.error(sql_get_random_drawing)
        ret_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_random_drawing)
                query_data = MysqlOper.get_query_result(cursor)
                for each_data in query_data:
                    pic_dict = {
                        "pic_id": each_data.get("pic_id"),
                        "pic_desc": each_data.get("pic_desc"),
                        "pic_url": settings.OSS_PREFIX + each_data.get("pic_url"),
                    }
                    ret_data.append(pic_dict)
            code = RET.OK
            message = Language.get(code)
            return CstResponse(
                code=code, message=message, data=ret_data, total=len(ret_data)
            )
        except Exception:
            print(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            return CstResponse(code=code, message=message)


class QuestionsSetEditView(APIView):
    @swagger_auto_schema(
        operation_id="212",
        tags=["智能体"],
        operation_summary="获取自定义选择框",
        operation_description="获取自定义选择框。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "question_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="问题ID/智能体ID"
                ),
            },
        ),
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
                            description="提交的问题集详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "options": openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "option_id": openapi.Schema(
                                                    type=openapi.TYPE_INTEGER,
                                                    description="选项ID",
                                                ),
                                                "option_value": openapi.Schema(
                                                    type=openapi.TYPE_STRING,
                                                    description="选项值",
                                                ),
                                            },
                                        ),
                                        description="问题选项列表",
                                    ),
                                    "info_type_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="当前字段输入框的类型id.",
                                    ),
                                    "info_type_name": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="当前字段输入框的类型名称.",
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题标题."
                                    ),
                                    "placeholder": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题占位符."
                                    ),
                                    "weight": openapi.Schema(
                                        type=openapi.TYPE_INTEGER, description="问题权重."
                                    ),
                                    "is_required": openapi.Schema(
                                        type=openapi.TYPE_BOOLEAN, description="问题是否必填."
                                    ),
                                },
                            ),
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
    # @cache_response(timeout=settings.CACHE_TIME, key_func=CstKeyConstructor(), cache='cache')
    def post(self, request):
        question_id = request.data.get("question_id")
        logger.error(request.data)

        sql_get_data = f"""
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
                    {settings.ADMIN_DB}.oq_question_info AS oq
                JOIN
                    {settings.ADMIN_DB}.oi_info_types AS oit ON oq.info_type_id = oit.info_type_id
                JOIN
                    {settings.ADMIN_DB}.oio_info_options AS oio ON FIND_IN_SET(oio.option_id, oq.option_ids)
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
                    oq.weight, oq.created_at

        """

        ret_data = []
        try:
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_get_data)
                query_data = MysqlOper.get_query_result(cursor)

                if not query_data:
                    code = RET.OK
                    message = Language.get(code)
                    frame = {
                        "type_id": '438600126748678',
                        "title": '你的提问',
                        "placeholder": '请输入内容',
                        "options": [{"option_id": 438689288239174, "value": "你的提问"}],
                        "is_required": "1",
                        "weight": "1",
                        "info_type_name": 'Textarea'
                    }
                    ret_data.append(frame)
                    return CstResponse(
                        code=code, message=message, data=ret_data)

                for each_data in query_data:
                    each_data_dict = {}
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
                        dictionary_list = {}

                    each_data_dict["options"] = dictionary_list
                    each_data_dict["info_type_id"] = info_type_id
                    each_data_dict["info_type_name"] = info_type_name
                    each_data_dict["title"] = title
                    each_data_dict["placeholder"] = placeholder
                    each_data_dict["weight"] = weight
                    each_data_dict["is_required"] = is_required
                    ret_data.append(each_data_dict)

                code = RET.OK
                message = Language.get(code)
                return CstResponse(code=code, message=message, data=ret_data)
        except Exception:
            logger.error(traceback.format_exc())
            code = RET.NETWORK_ERROR
            message = Language.get(code)
            return CstResponse(code=code, message=message)


class QuestionsSetSearch(APIView):
    serializer_class = QuestionsSetManageSerializer

    @swagger_auto_schema(
        operation_id="102",
        tags=["v5.2"],
        operation_summary="问题集搜索",
        operation_description="此端点允许用户搜索后获取问题集详情。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "keywords": openapi.Schema(
                    type=openapi.TYPE_STRING, description="关键字."
                ),
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="行业ID."
                ),
            },
        ),
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
                            description="返回结果详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "question_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题ID."
                                    ),
                                    "module_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属模块ID."
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题标题."
                                    ),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题内容."
                                    ),
                                    "content_hidden": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="隐藏内容."
                                    ),
                                    "industry_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属行业ID."
                                    ),
                                    "occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属职业ID."
                                    ),
                                    "sub_occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="所属二级职业ID.",
                                    ),
                                    "emp_duration_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间ID."
                                    ),
                                    "expertise_level_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平ID."
                                    ),
                                },
                            ),
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
    # @cache_response(timeout=settings.CACHE_TIME, key_func=CstKeyConstructor(), cache='cache')
    def post(self, request):

        data = request.data

        keywords = data.get("keywords")
        industry_id = data.get("industry_id")

        if not keywords:
            code = RET.OK
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=[], total=0)

        sql_search_question_set = (
            f"SELECT a.question_id, a.module_id, a.title,a.content, b.contact_qr_code,b.contact_qr_code_desc,"
            f" b.interest_group, b.interest_group_desc, c.character_avatar, "
            f" a.industry_id, a.occupation_id, a.sub_occu_id, "
            f"a.emp_duration_id, a.expertise_level_id, a.content_hidden FROM {settings.ADMIN_DB}.op_questions_set a "
            f"LEFT JOIN {settings.ADMIN_DB}.op_modules b ON a.module_id = b.module_id "
            f"LEFT JOIN {settings.ADMIN_DB}.uqd_user_question_details c ON a.question_id = c.question_id AND c.is_delete = 0 "
            f"WHERE a.title REGEXP '{keywords}'  AND a.is_delete = 0  AND a.is_hidden = 0  ")

        if industry_id:
            sql_search_question_set += f" AND a.industry_id = {industry_id}"

        try:
            logger.error(sql_search_question_set)
            with connections[settings.ADMIN_DB].cursor() as cursor:
                cursor.execute(sql_search_question_set)

                ret_data = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    data_dict = {}
                    data_dict["question_id"] = each.get("question_id")
                    data_dict["module_id"] = each.get("module_id")
                    data_dict["title"] = each.get("title")
                    data_dict["content"] = each.get("content")
                    data_dict["contact_qr_code"] = each.get("contact_qr_code")
                    data_dict["contact_qr_code_desc"] = each.get(
                        "contact_qr_code_desc", ""
                    )
                    data_dict["interest_group_code"] = each.get(
                        "interest_group")
                    data_dict["interest_group_code_desc"] = each.get(
                        "interest_group_desc", ""
                    )
                    data_dict["content_hidden"] = each.get("content_hidden")
                    data_dict["industry_id"] = each.get("industry_id")
                    data_dict["occupation_id"] = each.get("occupation_id")
                    data_dict["character_avatar"] = each.get(
                        "character_avatar")
                    data_dict["sub_occu_id"] = each.get("sub_occu_id")
                    data_dict["emp_duration_id"] = each.get("emp_duration_id")
                    data_dict["expertise_level_id"] = each.get(
                        "expertise_level_id")
                    ret_data.append(data_dict)
                code = RET.OK
                message = Language.get(code)
                return CstResponse(
                    code=code,
                    message=message,
                    data=ret_data,
                    total=len(ret_data))
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)


class GetOutputVideoData(APIView):
    serializer_class = QuestionsSetManageSerializer

    @swagger_auto_schema(
        operation_id="102",
        tags=["v5.2"],
        operation_summary="问题集搜索",
        operation_description="此端点允许用户搜索后获取问题集详情。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "keywords": openapi.Schema(
                    type=openapi.TYPE_STRING, description="关键字."
                ),
                "industry_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="行业ID."
                ),
            },
        ),
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
                            description="返回结果详情列表.",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "question_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题ID."
                                    ),
                                    "module_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属模块ID."
                                    ),
                                    "title": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题标题."
                                    ),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="问题内容."
                                    ),
                                    "content_hidden": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="隐藏内容."
                                    ),
                                    "industry_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属行业ID."
                                    ),
                                    "occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="所属职业ID."
                                    ),
                                    "sub_occu_id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        description="所属二级职业ID.",
                                    ),
                                    "emp_duration_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="从业时间ID."
                                    ),
                                    "expertise_level_id": openapi.Schema(
                                        type=openapi.TYPE_STRING, description="专业水平ID."
                                    ),
                                },
                            ),
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
    def post(self, request):

        data = request.data
        project_code = data.get("project_code", "")

        if not project_code:
            code = RET.PARAM_MISSING
            message = Language.get(code)
            return CstResponse(code=code, message=message, data=[], total=0)

        sql_get_time_duration = (
            f" SELECT time_length FROM {settings.DEFAULT_DB}.vd_digital_human_live_video_dtl WHERE"
            f" project_code = {project_code}")

        try:
            logger.info(sql_get_time_duration)
            with connection.cursor() as cursor:
                cursor.execute(sql_get_time_duration)

                time_legths = []
                result = MysqlOper.get_query_result(cursor)
                for each in result:
                    time_length = each.get("time_length")
                    time_legths.append(time_length)

                sum_value = sum(map(float, time_legths))
                rounded_up_sum = math.ceil(sum_value)

                sql_get_price = f"SELECT prod_price FROM {settings.DEFAULT_DB}.pp_products WHERE prod_id = 34"
                # f"  AND  is_show = 1 AND is_delete = 0 LIMIT 1"
                cursor.execute(sql_get_price)
                price_data = MysqlOper.get_query_result(cursor)
                price_data = price_data[0].get("prod_price")

                obj_minutes = math.ceil(Decimal(rounded_up_sum) / 60)
                total_amount = obj_minutes * Decimal(price_data)
                total_amount = total_amount.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

                dict_ret_data = {
                    "total_amount": total_amount,
                    "total_length": obj_minutes,
                }
                code = RET.OK
                message = Language.get(code)
                return CstResponse(
                    code=code, message=message, data=[dict_ret_data], total=1
                )
        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            error = str(traceback.format_exc())
            logger.error(error)
            raise CstException(code=code, message=message)
