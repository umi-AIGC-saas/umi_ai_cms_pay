#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/6/8 10:52
# @Author  : payne
# @File    : get_id.py
# @Description : 获取分布式ID


from utils.distributed_id_generator import generator, options


def get_distributed_id(worker_id):
    # 声明id生成器参数，需要自己构建一个worker_id
    option = options.IdGeneratorOptions(worker_id=worker_id)
    # 参数中，worker_id_bit_length 默认值6，支持的 worker_id 最大值为2^6-1，若 worker_id
    # 超过64，可设置更大的 worker_id_bit_length
    idgen = generator.DefaultIdGenerator()
    # 保存参数
    idgen.set_id_generator(option)
    # 生成id
    uid = idgen.next_id()
    # 打印出来查看
    return uid
