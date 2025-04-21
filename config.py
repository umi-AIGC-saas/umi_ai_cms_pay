#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/25 18:10
# @Author  : payne
# @File    : config.py
# @Description : extend setting config prod


import os

DEBUG = False

APPEND_SLASH = False

DEFAULT_DB = "chatai"
ADMIN_DB = "chatai_admin"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis地址
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {
                # "max_connections": 100,
                "decode_responses": True,
                # "socket_timeout": 10
            },
        },
    },
    "usage": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis地址
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {
                # "max_connections": 100,
                "decode_responses": True,
                # "socket_timeout": 10
            },
        },
    },
    "cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {
                # "max_connections": 100,
                # "socket_timeout": 10
            },
        },
    },
    "config": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {
                "decode_responses": True
                # "max_connections": 100,
                # "socket_timeout": 10
            },
        },
    },
    "lock": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
        },
    },
    "order": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
        },
    },
    "key": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {"decode_responses": True},
        },
    },
    "hashrate": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {"decode_responses": True},
        },
    },
    "prompts": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {"decode_responses": True},
        },
    },
    "questions": {
        "BACKEND": "django_redis.cache.RedisCache",
        # TODO 你的redis 密码
        "LOCATION": "",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # TODO 你的redis 密码
            "PASSWORD": "",
            "CONNECTION_POOL_KWARGS": {"decode_responses": True},
        },
    },
}

# TODO  你的MQ配置
MQ_HOST = ""

MQ = {
    "ty": {
        "USER": "",
        "PASSWORD": "",
        "HOST": MQ_HOST,
        "PORT": "",
        "vhost": "",
    }
}
# # TODO  你的DB配置
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "chatai",
        "USER": "root",
        "PASSWORD": "",
        "HOST": "",
        "PORT": 3306,
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    },
    ADMIN_DB: {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "chatai_admin",
        "USER": "root",
        "PASSWORD": "",
        "HOST": "",
        "PORT": 3306,
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"connect_timeout": 10},
    },
}

# TODO  你的HTTP 配置
config_url = ""
config_port = ""

prod_notify_url = "ai.umi6.com:28060"
# --------------------------TODO alipay-config-start-----------------------------------
# 支付宝 配置
app_id = ""
# 测试环境
app_notify_url = "https://{}/pay/update_order_alipay/".format(prod_notify_url)
return_url = ""

app_private_key_path = "utils/payment_keys/app_private.txt"
alipay_public_key_path = "utils/payment_keys/aplipay_public.txt"
app_public_key_path = "utils/payment_keys/app_public.txt"

# --------------------------TODO wechat-pay-config-start-----------------------------------
# NATIVE 支付
APP_ID = ""  # APPID
MCH_ID = ""  # 商户号
API_KEY = ""  # 32位 API密钥
APP_SECRECT = ""

UFDODER_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"  # 微信下单api
QUERY_URL = "https://api.mch.weixin.qq.com/pay/orderquery"
# 测试环境
# NOTIFY_URL =
# "https://{}/pay/update_order_wechat/".format('b5d6-240e-3b1-3482-7d30-bd56-e552-58e6-b741.ngrok-free.app')
# # 微信支付结果回调接口
# 微信支付结果回调接口
NOTIFY_URL = "https://{}/pay/update_order_wechat/".format(prod_notify_url)

# 多小程序段配置

# 小程序 1, 请使用自己的配置
MINI_PROGRAM_APP_ID = ""
MINI_PROGRAM_APP_SECRET = ""

# 小程序 2, 请使用自己的配置
UMI_MINI_PROGRAM_APP_ID = ""
UMI_MINI_PROGRAM_APP_SECRET = ""

# 小程序 3, 请使用自己的配置
WC_MINI_PROGRAM_APP_ID = ""
WC_MINI_PROGRAM_APP_SECRET = ""

# 小程序 4, 请使用自己的配置
ZN_MINI_PROGRAM_APP_ID = ""
ZN_MINI_PROGRAM_APP_SECRET = ""

# 获取openid
MWEB_AUTH = "https://api.weixin.qq.com/sns/oauth2/access_token"
XCX_AUTH = "https://api.weixin.qq.com/sns/jscode2session"

#  测试环境
CREATE_IP = config_url  # 服务器IP

# TODO 微信MP相关配置


# TODO OSS
ACCESS_KEY_ID = ""
ACCESS_KEY_SECRET = ""
BUCKET_NAME = ""
END_POINT = ""
NETWORK_STATION = ""


# 你的本地日志地址
if DEBUG:
    BASE_LOG_DIR = ""
else:
    BASE_LOG_DIR = "/var/log/"

LOGGING = {
    "version": 1,  # 保留字
    "disable_existing_loggers": False,  # 禁用已经存在的logger实例
    # 日志文件的格式
    "formatters": {
        # 详细的日志格式
        "standard": {
            "format": "[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%(filename)s:%(lineno)d]"
            "[%(levelname)s][%(message)s]"
        },
        # 简单的日志格式x
        "simple": {
            "format": "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%(message)s"
        },
    },
    # 过滤器
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    # 处理器
    "handlers": {
        # 在终端打印
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],  # 只有在Django debug为True时才在屏幕打印日志
            "class": "logging.StreamHandler",  #
            "formatter": "simple",
        },
        # 默认的
        "default": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",  # 保存到文件，自动切
            # 日志文件
            "filename": os.path.join(BASE_LOG_DIR, "chat_pay_info.log"),
            "maxBytes": 1024 * 1024 * 50,  # 日志大小 50M
            "backupCount": 3,  # 最多备份几个
            "formatter": "standard",
            "encoding": "utf-8",
        },
        # 专门用来记错误日志
        "error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",  # 保存到文件，自动切
            "filename": os.path.join(BASE_LOG_DIR, "chat_pay_err.log"),  # 日志文件
            "maxBytes": 1024 * 1024 * 50,  # 日志大小 50M
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        # 输出info日志
        "info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_LOG_DIR, "chat_pay_test.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",  # 设置默认编码
        },
    },
    "loggers": {
        "django": {
            "handlers": ["default", "console"],  # 来自上面定义的handlers内容
            "level": "INFO",
            "propagate": True,  # 是否继承父类的log信息
        },
        # sourceDns.webdns.views 应用的py文件
        "caches": {
            "handlers": ["default", "error"],
            "level": "INFO",
            "propagate": True,
        },
        "pay": {
            "handlers": ["error", "default", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "view": {
            "handlers": ["error", "default", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
    "SECURITY_DEFINITIONS": {
        "Token": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

# OSS prefix

OSS_PREFIX = "https://umi-intelligence.oss-cn-shenzhen.aliyuncs.com/"

# 缓存时间
CACHE_TIME = 60 * 10

# TODO 服务地址

SERVER_ADDRESS = ""

# 分销体系调用接口
SERVER_URL = "你的http地址:29090"
PAY_COMMISSION = "https://{}/api/user/pay_commission".format(SERVER_URL)
UPGRADE_DISTRIBUTION_LEVEL = "https://{}/api/user/upgrade_distribution".format(
    SERVER_URL
)


SUBMIT_VOICE = "https://{}/api/sv_voice/submit_customized_voice".format(
    "你的http地址:28083"
)

SUBMIT_SOUND_CLONE = "https://{}/api/sv_voice/volcengine_voice_train_pay".format(
    "你的http地址:28083"
)

# 初始化次数接口
INIT_VIP_FRAME_LIMIT = "{}/pay/token_manage_redis".format(SERVER_ADDRESS)

# 主动查询订单状态接口
ALIPAY_QUERY_ORDER_STATUS = "{}/pay/query_status_alipay/".format(
    SERVER_ADDRESS)
WECHAT_QUERY_ORDER_STATUS = "{}/pay/query_status_wechat/".format(
    SERVER_ADDRESS)

# 积分折算
POINTS_UNIT = 50

ADMIN_PUBLIC_API_DOMAIN = "你的http地址:8080/"
ADMIN_USER_BUILD_MODEL = "api/api/system/info_question_user_detail/"
ADMIN_INDUSTRY_DICT = "api/api/system/industry_dict/"
ADMIN_OCCUPATION_DICT = "api/api/system/occupation_dict/"
ADMIN_SEC_OCCUPATION_DICT = "api/api/system/sec_occupation_dict/"
ADMIN_DURATION_DICT = "api/api/system/duration_dict/"
ADMIN_EXPERTISE_LEVEL_DICT = "api/api/system/expertise_level_dict/"
ADMIN_MODULE_DICT = "api/api/system/modules_dict/"

# TODO 星火文档对话
SPARK_KNOWLEDGE_BASE_APP_ID = ""
SPARK_KNOWLEDGE_BASE_APP_SECRET = ""


# 新版计费中心接口【go version】

SERVER_BILL_URL = "你的http地址"
SERVER_BILL_PORT = "28071"

HASHRATE_ADDRESS = "/api/v1/hashrate"
HASHRATE_RENEW = "/api/v1/renew"
IS_ACTIVE_ADDRESS = "/api/v1/active"

