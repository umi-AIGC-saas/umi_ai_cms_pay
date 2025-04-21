"""
@Author				: cc
@Email				:
@Lost modifid		: 19-8-20 01:04
@Filename			: cst_class.py
@Description		: 日志   工具类
@Software           : PyCharm
"""
import logging

from rest_framework.response import Response

from language.language_pack import Language

logger = logging.getLogger(__name__)


class CstResponse(Response):
    def __init__(self, code, message=None, data=None, total=1, **kwargs):
        """
        自定义返回数据
        :param data: 返回数据
        :param code: 返回状态码
        :param message: 返回消息
        """
        if not message:
            message = Language.get(code)

        dic_data = dict(code=int(code), msg=message, total=total)
        if data:
            dic_data["data"] = data
        else:
            dic_data["data"] = []
        super(CstResponse, self).__init__(dic_data, **kwargs)


class CstException(Exception):
    """
    业务异常类
    """

    def __init__(self, code, message=None):
        self.code = code
        self.message = message
        super(CstException, self).__init__(message)


class ValidationError(Exception):
    """
    业务异常类
    """

    def __init__(self, code, message=None):
        self.code = code
        self.message = message
        super(ValidationError, self).__init__(message)
