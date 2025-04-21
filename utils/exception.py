"""
@Author				: WarmXiao
@Email				: warm.xiao@ecoprint.tech
@Lost modifid		: 19-8-20 01:04
@Filename			: exception.py
@Description		: 全局异常捕获
@Software           : PyCharm
"""

import logging
import traceback

from django.conf import settings
from django.db import DatabaseError
from redis.exceptions import RedisError
from rest_framework.views import exception_handler as drf_exception_handler

from language.language_pack import RET
from utils.cst_class import CstException, CstResponse, ValidationError

logger = logging.getLogger(__name__)


def exception_handler(exc, context):
    """
    自定义异常处理
    :param exc: 异常
    :param context: 异常上下文
    :return: Response响应对象
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        errmsg = None
        if settings.DEBUG:
            errmsg = str(exc)
        if isinstance(exc, DatabaseError) or isinstance(exc, RedisError):
            # 数据库异常
            logger.error(traceback.format_exc())
            response = CstResponse(RET.DB_ERR, errmsg)
        elif isinstance(exc, CstException):
            response = CstResponse(exc.code, exc.message)
        elif isinstance(exc, ValidationError):
            response = CstResponse(exc.code, exc.message)
        else:
            logger.error(traceback.format_exc())
            response = CstResponse(RET.SERVER_ERROR, errmsg)
    # if response and response.status_code == 400:
    #     logger.error(str(exc.detail))
    #     response = CstResponse(RET.DATAERR, exc.detail)
    #
    # if response and response.status_code != 200:
    #     logger.error(str(exc.detail))
    #     response = CstResponse(RET.DBERR, exc.detail)

    return response


class AliPayException(Exception):
    def __init__(self, code, message):
        self.__code = code
        self.__message = message

    def to_unicode(self):
        return "AliPayException: code:{}, message:{}".format(
            self.__code, self.__message
        )

    def __str__(self):
        return self.to_unicode()

    def __repr__(self):
        return self.to_unicode()


class AliPayValidationError(Exception):
    pass
