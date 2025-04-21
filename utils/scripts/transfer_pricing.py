#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/7/6 17:26
# @Author  : payne
# @File    : transfer_pricing.py
# @Description : 计价方式转换
import math

import redis


def transfer_db(orgin_bd, target_db):
    # 创建一个连接到Redis的客户端

    r = redis.Redis(
        host="r-bp16ttreemkoyqrip7pd.redis.rds.aliyuncs.com",
        port=6379,
        db=orgin_bd,
        password="Hdxx123456",
    )

    # 连接到要复制到的数据库
    r_target = redis.Redis(
        host="r-wz9jjgi3vbxr23cphcpd.redis.rds.aliyuncs.com",
        port=6379,
        db=target_db,
        password="Hdxx123456",
    )
    print(r_target.ping())
    # 获取所有的key
    keys = r.keys("*")
    for key in keys:
        # 使用dump获取二进制表示的值
        value_dump = r.dump(key)
        # 使用restore将值复制到新的数据库
        # 在这个例子中，我们使用了0作为TTL，这意味着没有过期时间
        r_target.restore(key, 0, value_dump)


for i in range(1000):
    transfer_db(i, i)
    print(f"db {i} done")

# import math
#
#
# def transfer_unit_common():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "13": 0.004,
#         "14": 0.065,
#         "22": 0.004,
#         "23": 0.004,
#         "24": 50,
#         "15": 35,
#         "16": 35,
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         if 'package' in key_str and 'universal' not in key_str and 'packages' not in key_str:
#             key_parts = key_str.split(':')
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
#
#
#
# def transfer_unit_total_common():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "13": 0.004,
#         "14": 0.065,
#         "22": 0.004,
#         "23": 0.004,
#         "24": 50,
#         "15": 35,
#         "16": 35,
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     print(points)
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             print(points)
#
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         print(key_str)
#         if 'total_count' in key_str and 'total_count_origin' not in key_str:
#             key_parts = key_str.split(':')
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
#
#
# def transfer_unit_total_origin_common():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "13": 0.004,
#         "14": 0.065,
#         "22": 0.004,
#         "23": 0.004,
#         "24": 50,
#         "15": 35,
#         "16": 35,
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     print(points)
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             print(points)
#
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         print(key_str)
#         if 'total_count_origin' in key_str:
#             key_parts = key_str.split(':')
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
#
#
# def transfer_unit_universal():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "18": 50,
#         "19": 50,
#         "20": 50,
#         "21": 50
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     print(points)
#
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             print(points)
#
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         # print(key)
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         if 'universal_package' in key_str and 'packages' not in key_str:
#             key_parts = key_str.split(':')
#             print(key_str)
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
#
# def transfer_unit_total_universal():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "18": 50,
#         "19": 50,
#         "20": 50,
#         "21": 50
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     print(points)
#
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             print(points)
#
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         # print(key)
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         if 'total_price' in key_str and 'total_price_origin' not in key_str:
#             key_parts = key_str.split(':')
#             print(key_str)
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
#
#
#
# def transfer_unit_total_origin_universal():
#     r = redis.Redis(host='r-wz91qwmi28p208tlaqpd.redis.rds.aliyuncs.com', port=6379, db=16, password='Hdxx123456')
#
#     # 定义产品id到积分转换比例的映射
#     prod_to_points = {
#         "18": 50,
#         "19": 50,
#         "20": 50,
#         "21": 50
#     }
#
#     def convert_values(key, prod_id):
#         key_type = r.type(key).decode('utf-8')
#
#         # 将所有的value换算成积分并写回
#         if key_type == 'hash':
#             values = r.hgetall(key)
#             for field, value in values.items():
#                 field_str = field.decode('utf-8')
#                 if field_str == "expire_at":
#                     continue
#                 else:
#                     points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                     print(points)
#
#                     r.hset(key, field, points)
#         elif key_type == 'string':
#             value = r.get(key)
#             points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#             print(points)
#
#             r.set(key, points)
#         elif key_type == 'list':
#             values = r.lrange(key, 0, -1)  # 获取列表所有元素
#             for i, value in enumerate(values):
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.lset(key, i, points)
#         elif key_type == 'set':
#             values = r.smembers(key)  # 获取集合所有元素
#             for value in values:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#
#                 r.srem(key, value)
#                 r.sadd(key, points)
#         elif key_type == 'zset':
#             values_with_scores = r.zrange(key, 0, -1, withscores=True)  # 获取有序集合所有元素及其分数
#             for value, score in values_with_scores:
#                 points = math.ceil(float(value.decode('utf-8')) * prod_to_points.get(prod_id, 1))
#                 print(points)
#                 r.zadd(key, {value: points})
#         else:
#             print(f'Unsupported type: {key_type}')
#
#     keys = r.keys('*')
#
#     for key in keys:
#         # print(key)
#         key_str = key.decode('utf-8')  # 将键从字节转换为字符串
#         if 'total_price_origin' in key_str:
#             key_parts = key_str.split(':')
#             print(key_str)
#             prod_id = key_parts[2]
#             convert_values(key, prod_id)
# transfer_unit_common()
# transfer_unit_total_origin_universal()
# transfer_unit_total_common()
#
# transfer_unit_total_origin_common()
# transfer_unit_universal()
#
#
# transfer_unit_total_universal()
