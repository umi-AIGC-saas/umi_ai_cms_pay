#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 17:05
# @Author  : payne
# @File    : my_decorators.py
# @Description :
import logging
import traceback
from decimal import Decimal
from functools import wraps

import wrapt as wrapt
from django.conf import settings
from django.db import connection, connections
from language.language_pack import RET, Language
from utils.cst_class import CstException, CstResponse
from utils.sql_oper import MysqlOper

logger = logging.getLogger("view")


class ValidateAmount(object):
    def __init__(self, param):
        self.param = param
        self.db = self.param.get("db")
        self.logger = self.param.get("logger")

    def __setitem__(self, k, v):
        self.k = v

    @wrapt.decorator
    def __call__(self, wrapped, instance, args, kwargs):
        for arg in args:
            request = arg
        data = request.data
        prod_id = data.get("prod_id")
        total_amount = data.get("total_amount")
        quantity = data.get("quantity")

        # 输出视频商品不需要校验
        if int(prod_id) == 34:
            args[0].__dict__["validate_amount_pass"] = True

        sql_check_price = f"SELECT  prod_price FROM {settings.DEFAULT_DB}.pp_products WHERE prod_id = {prod_id}"

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_check_price)
                query_data = MysqlOper.get_query_result(cursor)
                prod_price = query_data[0].get("prod_price")
                total_amount_check = Decimal(prod_price) * Decimal(quantity)

        except Exception:
            code = RET.DB_ERR
            message = Language.get(code)
            args[0].__dict__["validate_amount_pass"] = False
            logger.info(traceback.format_exc())
            raise CstException(code=code, message=message)
        if float(total_amount_check) == float(total_amount):
            args[0].__dict__["validate_amount_pass"] = True
        else:
            args[0].__dict__["validate_amount_pass"] = False
        return wrapped(*args, **kwargs)


class ExperienceCardRejectSecPurchase(object):
    def __init__(self, param):
        self.param = param
        self.db = self.param.get("db")
        self.logger = self.param.get("logger")

    def __setitem__(self, k, v):
        self.k = v

    @wrapt.decorator
    def __call__(self, wrapped, instance, args, kwargs):
        for arg in args:
            request = arg
        data = request.data

        user_id = data.get("user_id")
        prod_id = data.get("prod_id", 0)
        activate_code = data.get("activate_code")

        if int(prod_id) == 0:
            # check activate_code details
            sql_code_status = (
                f"SELECT to_prod_id  FROM "
                f"{settings.ADMIN_DB}.oa_activate_code WHERE activate_code = '{activate_code}' AND "
                f" NOW() < expired_date AND is_delete = 0")

            try:
                with connections[settings.ADMIN_DB].cursor() as cursor:
                    cursor.execute(sql_code_status)
                    result = MysqlOper.get_query_result(cursor)
                    if result:
                        prod_id = result[0].get("to_prod_id")
                    else:
                        code = RET.CODE_INVALID
                        message = Language.get(code)
                        logger.info(traceback.format_exc())
                        return CstResponse(code=code, message=message)
            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                logger.info(traceback.format_exc())
                raise CstException(code=code, message=message)

        if int(prod_id) == 12:
            sql_order_history = (
                f"SELECT po_orders.user_id, po_orders_items.prod_id FROM po_orders JOIN po_orders_items ON "
                f"po_orders.order_id = po_orders_items.order_id WHERE po_orders.user_id = {user_id} "
                f"AND po_orders_items.prod_id = 12 AND po_orders.status = 2 LIMIT 1 ")

            print(sql_order_history)

            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_order_history)
                    rowcount = cursor.rowcount

                    if rowcount:
                        code = RET.REJECT
                        message = Language.get(code)
                        return CstResponse(code=code, message=message)

            except Exception:
                code = RET.DB_ERR
                message = Language.get(code)
                logger.info(traceback.format_exc())
                return CstResponse(code=code, message=message)

        return wrapped(*args, **kwargs)


def close_old_connections():
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()


def handle_db_connections(func):
    def func_wrapper(*args, **kwargs):
        close_old_connections()
        logger.info("处理连接")
        result = func(*args, **kwargs)
        close_old_connections()

        return result

    return func_wrapper
