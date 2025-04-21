#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 17:07
# @Author  : payne
# @File    : gadgets.py
# @Description :


# 小功能
import base64
import json
import os
import random
import time
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, getcontext

import docx
import PyPDF2
import requests
from django.conf import settings
from django.db import connection, transaction
from django_redis import get_redis_connection
from openai import OpenAI
from rest_framework_extensions.key_constructor.constructors import \
    DefaultKeyConstructor

from utils.OSS.tooss import Tooss
from utils.sql_oper import MysqlOper


class gadgets(object):
    def __init__(self):
        super(gadgets, self).__init__()

    # 基于当前时间生成类似订单号的数据类型 eg: 20190212112387658
    @staticmethod
    def set_flow():
        base_code = datetime.now().strftime("%Y%m%d%H%M%S")
        order_list = []
        count = 1
        while True:
            if count > 100:
                break
            count_str = str(count).zfill(8)
            if base_code + count_str in order_list:
                continue
            order_list.append(base_code + count_str)
            count += 1
        return random.choice(order_list)

    @staticmethod
    def str_to_ts(str):
        # 字符类型的时间
        # 转为时间数组
        timeArray = time.strptime(str, "%Y-%m-%d %H:%M:%S")
        # timeArray可以调用tm_year等
        # 转为时间戳
        timeStamp = int(time.mktime(timeArray))
        return timeStamp

    # base64编码
    @staticmethod
    def ibase64_encode(content):
        encode_str = base64.b64encode(content.encode("utf-8"))
        encode_str = str(encode_str, "utf-8")
        return encode_str

    # base64 解码
    @staticmethod
    def ibase64_decode(content):
        decode_str = base64.b64decode(content.encode("utf-8"))
        decode_str = str(decode_str, "utf-8")
        return decode_str

    @staticmethod
    @transaction.atomic()
    def insert_new_member(order_id, conn, vip=False, expire_at="", pay=False):

        save_id = transaction.savepoint()
        try:
            # 非卡密兑换，正常购买会员，因为是回调接口，拿不到用户的user_id， 所以需要根据order_id 来执行逻辑
            if pay:
                # 找出user_id
                sql_get_user_id = (
                    f"SELECT user_id FROM {settings.DEFAULT_DB}.po_orders WHERE order_id = {order_id}  A"
                    f"ND prod_cate_id = 3 LIMIT 1")
                with connection.cursor() as cursor:
                    cursor.execute(sql_get_user_id)
                    get_user_id_result = MysqlOper.get_query_result(cursor)
                    user_id = get_user_id_result[0].get("user_id")

                # 检查是否已经是会员状态
                sql_check_vip = (
                    f"SELECT expire_at FROM {settings.DEFAULT_DB}.pm_membership WHERE user_id = '{user_id}' "
                    f"AND UNIX_TIMESTAMP(NOW()) < expire_at AND status = 1 ORDER BY expire_at DESC LIMIT 1")
                with connection.cursor() as cursor:
                    cursor.execute(sql_check_vip)
                    result = MysqlOper.get_query_result(cursor)
                    if result:
                        expire_at = result[0].get("expire_at")
                        vip = 1
                    else:
                        vip = 0
                        expire_at = 0

            time_difference = int(expire_at) - int(time.time())

            print(time_difference)
            print(vip)
            print("current time different and vip")
            if vip and time_difference > 0:

                # TODO 如果是vip， 则插入的expire_at 为 CAST(UNIX_TIMESTAMP(DATE_ADD(NOW(), INTERVAL pp.valid_period_days
                #  DAY)) AS UNSIGNED) AS expire_integer 加上 time_difference
                sql = f"""
                       INSERT INTO {settings.DEFAULT_DB}.pm_membership (user_id, order_id, start_at, expire_at, created_at, updated_at)
                       SELECT po.user_id, po.order_id, CAST(UNIX_TIMESTAMP(NOW()) AS UNSIGNED) AS now_integer,
                       CAST(UNIX_TIMESTAMP(DATE_ADD(NOW(), INTERVAL pp.valid_period_days DAY)) AS UNSIGNED) + {time_difference} AS expire_integer,
                       NOW(), NOW()
                       FROM po_orders po
                       JOIN po_orders_items poi ON po.order_id = poi.order_id
                       JOIN pp_products pp ON poi.prod_id = pp.prod_id
                       WHERE po.order_id = '{order_id}'  AND poi.prod_cate_id = 3
                       LIMIT 1;
                    """
            else:
                sql = f"""
                       INSERT INTO {settings.DEFAULT_DB}.pm_membership (user_id, order_id, start_at, expire_at, created_at, updated_at)
                       SELECT po.user_id, po.order_id, CAST(UNIX_TIMESTAMP(NOW()) AS UNSIGNED) AS now_integer,
                        CAST(UNIX_TIMESTAMP(DATE_ADD(NOW(), INTERVAL pp.valid_period_days DAY)) AS UNSIGNED) AS expire_integer, NOW(), NOW()
                       FROM po_orders po
                       JOIN po_orders_items poi ON po.order_id = poi.order_id
                       JOIN pp_products pp ON poi.prod_id = pp.prod_id
                       WHERE po.order_id = {order_id} AND poi.prod_cate_id = 3
                       LIMIT 1;
                   """
            print(sql)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    rowcount = cursor.rowcount
                    print(rowcount)
                    print(
                        "rowcount insert membership: {}".format(
                            str(rowcount)))
                    if rowcount == 1:
                        # transaction.savepoint_commit(save_id)
                        return True
                    else:
                        transaction.savepoint_rollback(save_id)
                        return False
            except Exception:
                print(traceback.format_exc())
                transaction.savepoint_rollback(save_id)
                return False
        except Exception as e:
            print(traceback.format_exc())
            return False

    @staticmethod
    @transaction.atomic()
    def insert_data_plus(user_id, prod_id, order_id, quantity, price):

        r_config = get_redis_connection("config")
        ids_to_update = [prod_id]  # 默认为输入的prod_id
        product_tokens = r_config.get("config:{}".format(prod_id))

        # 设定 decimal 全局精度为 8 位
        getcontext().prec = 8

        sucess_count = 0

        for id_to_update in ids_to_update:
            sql_get_prod_details = (
                f"SELECT valid_period_days FROM {settings.DEFAULT_DB}.pp_products"
                f" WHERE prod_id = {id_to_update} AND is_delete = 0")
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql_get_prod_details)
                    ret_data = MysqlOper.get_query_result(cursor)

                    if ret_data:
                        valid_days = ret_data[0].get("valid_period_days")
                        days = int(valid_days) * int(quantity)
                        expire_at = (
                                datetime.now() +
                                timedelta(
                                    days=days)).timestamp()
                    else:
                        return False
            except Exception:
                print(traceback.format_exc())
                return False
            try:
                if int(prod_id) in [18, 19, 20, 21, 25, 26]:  # 通用流量包

                    total_price = Decimal(
                        json.loads(product_tokens)["price"]
                    ) * Decimal(quantity)

                    # 直接存储通用流量包的总价格和有效期到 Redis
                    r_usage = get_redis_connection("usage")
                    package_key = (
                        f"universal_package:{user_id}:{id_to_update}:{order_id}"
                    )
                    r_usage.hmset(
                        package_key, {
                            "total_price": str(
                                int(total_price) * settings.POINTS_UNIT), "expire_at": str(expire_at), }, )
                    r_usage.zadd(
                        f"universal_packages:{user_id}:{id_to_update}",
                        {package_key: str(expire_at)},
                    )

                    r_usage.incrbyfloat(
                        f"total_price:{user_id}:{id_to_update}",
                        int(total_price) * settings.POINTS_UNIT,
                    )
                    r_usage.incrbyfloat(
                        f"total_price_origin:{user_id}:{id_to_update}",
                        int(total_price) * settings.POINTS_UNIT,
                    )
                    sucess_count += 1
                else:
                    count = int(r_config.get(f"config:{id_to_update}"))

                    r_usage = get_redis_connection("usage")

                    package_key = f"package:{user_id}:{id_to_update}:{order_id}"
                    r_usage.hmset(
                        package_key, {
                            "count": count, "expire_at": str(expire_at)})
                    r_usage.zadd(
                        f"packages:{user_id}:{id_to_update}",
                        {package_key: str(expire_at)},
                    )

                    r_usage.incrbyfloat(
                        f"total_count:{user_id}:{id_to_update}", count)
                    r_usage.incrbyfloat(
                        f"total_count_origin:{user_id}:{id_to_update}", count
                    )
                    sucess_count += 1
            except Exception:
                print(traceback.format_exc())
                return False

        if len(ids_to_update) == sucess_count:
            return True
        else:
            return False

    @staticmethod
    def extend_pay_commission(user_id, order_id, amount, is_upgrade):
        try:
            api_pay_commission = settings.PAY_COMMISSION
            print(api_pay_commission)

            data = {
                "user_code": user_id,
                "order_no": order_id,
                "amount": amount,
                "is_upgrade": is_upgrade,
            }
            response = requests.post(url=api_pay_commission, data=data)

            print(response.text)
            content = response.json()
            if int(content.get("code")) == 20000:
                return True
            else:
                return False

        except Exception:
            print(traceback.format_exc())

    @staticmethod
    def extend_upgrade_distribution_level(user_id):
        print(222222222222)
        try:
            api_upgrade_distribution_level = settings.UPGRADE_DISTRIBUTION_LEVEL
            data = {"user_code": user_id, "level_type": "2"}
            response = requests.post(
                url=api_upgrade_distribution_level, data=data)
            print(response.text)
            content = response.json()
            if int(content.get("code")) == 20000:
                return True
            else:
                return False
        except Exception:
            print(traceback.format_exc())

    @staticmethod
    def is_vip(user_id, conn):
        # 检查是否已经是会员状态
        sql_check_vip = f"SELECT 1 FROM pm_membership WHERE user_id = '{user_id}' AND UNIX_TIMESTAMP(NOW()) < expire_at"

        with conn.cursor() as cursor:
            cursor.execute(sql_check_vip)
            rowcount = cursor.rowcount

            if rowcount:
                return True
            else:
                return False

    @staticmethod
    def recursive_defaultdict():
        return defaultdict(gadgets.recursive_defaultdict)

    @staticmethod
    def is_expired_count(db_expire_date):
        db_expire_date = datetime.fromisoformat(db_expire_date)
        current_date = datetime.now()
        if current_date > db_expire_date:
            return False
        else:
            return True

    @staticmethod
    def user_rest_value_redis(prod_id, user_id, prod_cate_id, r_connect):
        if int(prod_cate_id) == 6:

            key = f"total_price:{user_id}:{prod_id}"
        else:
            key = f"total_count:{user_id}:{prod_id}"

        value = r_connect.get(key)
        return str(value) if value else "0"

    @staticmethod
    def update_out_video_status(order_id):

        # 输出视频调用
        sql_get_prod_id = f"""
         SELECT live_code, prod_id
               FROM {settings.DEFAULT_DB}.po_orders_items
               WHERE order_id = {order_id}

        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_prod_id)
                data = MysqlOper.get_query_result(cursor)
                prod_id = data[0].get("prod_id")
        except Exception:
            print(traceback.format_exc())
            # 发生异常时回滚事务
            return False

        if int(prod_id) != 34:
            return True

        sql_update_make_status_video_dtl = f"""
            UPDATE {settings.DEFAULT_DB}.vd_digital_human_project
               SET project_status = 0
               WHERE project_code IN (SELECT live_code
               FROM {settings.DEFAULT_DB}.po_orders_items
               WHERE order_id = {order_id}) LIMIT 1
        """

        try:
            with connection.cursor() as cursor:

                cursor.execute(sql_update_make_status_video_dtl)
                rowcount_video_dtl = cursor.rowcount

                if rowcount_video_dtl > 0:
                    return True
                else:
                    return False
        except Exception:
            print(traceback.format_exc())
            # 发生异常时回滚事务
            cursor.execute("ROLLBACK")
            return False

    @staticmethod
    def update_clone_status(order_id):

        # 形象克隆调用
        sql_get_prod_id = f"""
         SELECT live_code, prod_id
               FROM {settings.DEFAULT_DB}.po_orders_items
               WHERE order_id = {order_id}

        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_prod_id)
                data = MysqlOper.get_query_result(cursor)
                prod_id = data[0].get("prod_id")
        except Exception:
            print(traceback.format_exc())
            # 发生异常时回滚事务
            return False

        if int(prod_id) != 33:
            return True

        # 形象克隆
        sql_update_make_status_video = f"""
            UPDATE {settings.DEFAULT_DB}.vd_digital_human_live_video
               SET make_status = 0
               WHERE live_code IN (SELECT live_code
               FROM {settings.DEFAULT_DB}.po_orders_items
               WHERE order_id = {order_id}) LIMIT 1
        """

        print(sql_update_make_status_video)
        try:
            with connection.cursor() as cursor:
                # 开始事务
                cursor.execute(sql_update_make_status_video)
                rowcount_video = cursor.rowcount
                if rowcount_video > 0:
                    return True
                else:
                    return False
        except Exception:
            print(traceback.format_exc())
            # 发生异常时回滚事务
            cursor.execute("ROLLBACK")
            return False

    @staticmethod
    def call_huoshan_sound_clone(order_id):

        # 形象克隆调用
        sql_get_prod_id = f"""
             SELECT  a.prod_id, b.user_id
                   FROM {settings.DEFAULT_DB}.po_orders_items a LEFT JOIN {settings.DEFAULT_DB}.po_orders b
                   ON a.order_id = b.order_id 
                   WHERE a.order_id = {order_id} AND a.is_delete = 0

            """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_get_prod_id)
                data = MysqlOper.get_query_result(cursor)
                prod_id = data[0].get("prod_id")
                user_id = data[0].get("user_id")
        except Exception:
            print(traceback.format_exc())
            # 发生异常时回滚事务
            return False

        if int(prod_id) != 43:
            return True

        response = requests.post(
            data={
                'user_code': user_id
            },
            url=settings.SUBMIT_SOUND_CLONE
        )
        print(settings.SUBMIT_SOUND_CLONE)
        print("settings.SUBMIT_SOUND_CLONEsettings.SUBMIT_SOUND_CLONEsettings.SUBMIT_SOUND_CLONEsettings.SUBMIT_SOUND_CLONE")
        if response.status_code == 200:
            res_data = json.loads(response.text)
            if res_data.get('code') == 20000:
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def submit_customized_voice(order_id):

        sql_update_make_status = f"""
         SELECT live_code, prod_id
               FROM {settings.DEFAULT_DB}.po_orders_items
               WHERE order_id = {order_id}

        """
        print(sql_update_make_status)
        print(
            "sql_update_make_statussql_update_make_statussql_update_make_statussql_update_make_statussql_update_make_status"
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_update_make_status)
                data = MysqlOper.get_query_result(cursor)
                live_code = data[0].get("live_code")
                prod_id = data[0].get("prod_id")

                print(
                    "submit_customized_voicesubmit_customized_voicesubmit_customized_voicesubmit_customized_voice"
                )
                print(prod_id)
                if int(prod_id) != 32:
                    submit_success = True
                else:
                    form_data = {"voice_code": live_code}
                    print(settings.SUBMIT_VOICE)
                    call_submit_customized_voice = requests.put(
                        url=settings.SUBMIT_VOICE, data=form_data
                    )
                    if call_submit_customized_voice.status_code == 200:
                        print(call_submit_customized_voice.text)
                        print("[[[[[[[[[[[[[[[[")
                        call_submit_customized_voice_data = json.loads(
                            call_submit_customized_voice.text
                        )
                        if call_submit_customized_voice_data.get(
                                "code") == 20000:
                            submit_success = True
                        else:
                            submit_success = False
                    else:
                        submit_success = False
        except Exception:
            print(traceback.format_exc())
            submit_success = False
        return submit_success

    @staticmethod
    def get_api_key(key):
        pattern = key + "_*"
        with get_redis_connection("key") as r_config:
            keys = r_config.keys(pattern)
            values = [r_config.get(each) for each in keys]  # 获取每个键对应的值
            return values

    @staticmethod
    def download_file(url, save_path):

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.exceptions.RequestException:
            return False

    @staticmethod
    def count_pages(file_path, file_type):
        try:
            if file_type == "pdf":
                with open(file_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    return len(reader.pages)

            elif file_type == "docx":
                doc = docx.Document(file_path)
                # 这里只是一个估算，实际页数可能因格式而异
                return len(doc.paragraphs) // 30

            elif file_type in ["md", "txt"]:
                with open(file_path, "r") as file:
                    # 基于每页大约 40 行来估算
                    return sum(1 for line in file) // 40

            else:
                return 0

        except Exception:
            print(traceback.format_exc())
            return -1

    @staticmethod
    def operate_hashrates(user_id, hashrate, scene=2):
        req_url = (
                settings.SERVER_BILL_URL
                + ":"
                + settings.SERVER_BILL_PORT
                + settings.HASHRATE_ADDRESS
        )
        try:
            req_data = {
                "user_id": user_id,
                "scene": scene,
                "hashrate": hashrate}
            response = requests.put(url=req_url, data=req_data)

            if response.status_code == 200:
                res_data = json.loads(response.text)
                if res_data.get("code") == 20000:
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            print(traceback.format_exc())
            return False

    @staticmethod
    def summarize_complimentary_hash_rates(user_id):
        # Key pattern to match
        key_pattern = f"complimentary:user:{user_id}:hashrate"

        # List to store the results
        results = []

        # Find all keys that match the pattern
        with get_redis_connection("hashrate") as r:
            keys = r.keys(key_pattern)
            # Iterate over keys and retrieve the data
            for key in keys:
                # Retrieving all elements in the sorted set
                hash_rate_data = r.zrange(key, 0, -1, withscores=True)

                # Deserialize each item and append to the results list
                for item, score in hash_rate_data:
                    data = json.loads(item)
                    results.append(data)
        return results

    @staticmethod
    def get_speech_response(user_id, session_code, character, llm_answer, speech_order, unique_name):
        save_audio_path = f"./speech/{user_id}/{session_code}"

        if not os.path.exists(save_audio_path):
            os.makedirs(save_audio_path, exist_ok=True)

        speech_name = str(speech_order) + '-' + unique_name
        save_audio_path += f'/{str(speech_name)}.mp3'

        try:
            # 这里假设 OpenAI 已正确设置
            with OpenAI(
                    api_key="sk-aWlXvBleYj9FiZZ176A4B2Be9aBc4dBcA70a0d498eFf7e18",
                    base_url='https://openai.qiheweb.com/v1'
            ) as client:
                print(client.base_url)
                print(client.api_key)
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=character,
                    input=llm_answer
                )
                if response.response.status_code == 200:
                    response.stream_to_file(save_audio_path)
                    return True
        except Exception:
            print(traceback.format_exc())
            return False

    @staticmethod
    def save_2_oss(user_id, session_code, speech_order, unique_name):
        speech_name = str(speech_order) + '-' + unique_name

        save_audio_path = f"./speech/{user_id}/{session_code}"

        if not os.path.exists(save_audio_path):
            os.makedirs(save_audio_path, exist_ok=True)

        save_audio_path += f'/{speech_name}.mp3'
        speech_oss_url = Tooss.main(imgUrl='', cate=f'speech/{user_id}/{session_code}',
                                    name=speech_name + '.mp3',
                                    local=True,
                                    local_path=save_audio_path)

        if not speech_oss_url:
            try:
                os.remove(save_audio_path)
            except Exception:
                print(traceback.format_exc())
            return False

        return speech_oss_url[0]

    @staticmethod
    def create_speech(speech_request: dict):
        try:
            unique_name = str(uuid.uuid4())
            response = gadgets.get_speech_response(speech_request['user_id'],
                                                   speech_request['session_code'],
                                                   speech_request['character'],
                                                   speech_request['llm_answer'],
                                                   speech_request['speech_order'],
                                                   unique_name)
            if response:
                print(response)
                save_to_oss = gadgets.save_2_oss(speech_request['user_id'], speech_request['session_code'],
                                                 speech_request['speech_order'], unique_name)
                if not save_to_oss:
                    return False
            else:
                return False
            speech_name = str(speech_request['speech_order']) + '-' + unique_name

            os.remove(f"./speech/{speech_request['user_id']}/{speech_request['session_code']}/{speech_name}.mp3")
            return save_to_oss
        except Exception:
            print(traceback.format_exc())
            return False


class CstKeyConstructor(DefaultKeyConstructor):
    def get_data_from_bits(self, **kwargs):
        result_dict = {}
        for bit_name, bit_instance in self.bits.items():
            if bit_name in self.params:
                params = self.params[bit_name]
            else:
                try:
                    params = bit_instance.params
                except AttributeError:
                    params = None
            result_dict[bit_name] = bit_instance.get_data(
                params=params, **kwargs)

        request = kwargs.get("request")
        if request.method in ["POST", "PUT"]:
            data = request.data
        else:
            data = request.query_params

        for key in data.keys():
            result_dict[key] = data[key]

        return result_dict
