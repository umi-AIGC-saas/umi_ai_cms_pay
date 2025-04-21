#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/6/27 16:09
# @Author  : payne
# @File    : query_order_status.py
# @Description :
import json
import time
import traceback
from threading import Lock, Thread

import requests
from django.apps import AppConfig
from django.conf import settings
from django_redis import get_redis_connection


class QueryOrderStatusQueue(object):

    lock = Lock()

    @staticmethod
    def process_order(order_id, method, source):

        if method == "alipay":
            api_request_url = settings.ALIPAY_QUERY_ORDER_STATUS
        else:
            api_request_url = settings.WECHAT_QUERY_ORDER_STATUS
        data = {"order_id": order_id, "source": source}

        response = requests.post(url=api_request_url, data=data)
        if response.status_code == 200:
            if response.text == "success":
                return True

            res_data = response.json()

            if res_data.get("code") == 20000:
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def push_order_to_queue(order_data):
        r = get_redis_connection("order")
        r.publish("orders", json.dumps(order_data))

    @staticmethod
    def mark_order_as_processed(order_id):
        r = get_redis_connection("order")
        r.publish("processed_orders", order_id)

    @staticmethod
    def order_listener():
        r = get_redis_connection("order")
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe("orders")
        for message in p.listen():
            order_data = json.loads(message["data"])
            order_id = order_data.get("order_id")
            source = order_data.get("source")
            method = order_data.get("method")
            if order_data["retry_count"] > 0:
                try:
                    with QueryOrderStatusQueue.lock:  # 使用锁来保护资源访问
                        process_result = QueryOrderStatusQueue.process_order(
                            order_id, method, source
                        )
                    if process_result:
                        continue
                    else:
                        with QueryOrderStatusQueue.lock:  # 使用锁来保护资源访问
                            order_data["retry_count"] -= 1
                            print(
                                "current count {}".format(
                                    order_data["retry_count"]))
                            r.publish("orders", json.dumps(order_data))
                        time.sleep(2)
                except Exception as e:
                    print(traceback.format_exc())
                    with QueryOrderStatusQueue.lock:  # 使用锁来保护资源访问
                        order_data["retry_count"] -= 1
                        print(
                            "current count {}".format(
                                order_data["retry_count"]))

                        r.publish("orders", json.dumps(order_data))
                    time.sleep(2)
            else:
                print(
                    f"Order {order_data['order_id']} has been retried 10 times and will be discarded."
                )


class QueryOrderStatusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sp_pay"

    def ready(self):
        print("QueryOrderStatus starting........")
        num_threads = 1  # 设置线程数量
        threads = []

        for _ in range(num_threads):
            thread = Thread(target=QueryOrderStatusQueue.order_listener)
            thread.start()
            threads.append(thread)
