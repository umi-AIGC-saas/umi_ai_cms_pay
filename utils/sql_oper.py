#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 11:12
# @Author  : payne
# @File    : sql_oper.py
# @Description : sql 操作相关

import logging

import pymysql

logger = logging.getLogger('view')


class MysqlOper(object):
    def __init__(self):
        super(MysqlOper, self).__init__()

    @staticmethod
    def get_query_result(cursor):
        result = []
        names = cursor.description
        datas = cursor.fetchall()

        logger.info(
            "current execute sql \n{}\nrowcount : {}\nrownumber : {}\narraysize : {}\ninsert_id : {}".format(
                cursor._executed,
                cursor.rowcount,
                cursor.rownumber,
                cursor.arraysize,
                cursor._result.insert_id,
            )
        )
        for rows in datas:
            one = {}
            for i in range(len(rows)):
                one[names[i][0]] = str(
                    rows[i]) if rows[i] or rows[i] == 0 else ""
                # one[names[i][0]] = str(rows[i])
            result.append(one)
        return result

    @staticmethod
    def format_sql(sql, params):
        formatted_sql = sql

        if params:
            formatted_params = tuple(
                pymysql.converters.escape_item(
                    param, "utf8") for param in params)
            formatted_sql = sql % formatted_sql
        return formatted_sql
