#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/10/28 14:21
# @Author  : payne
# @File    : spark_utils.py
# @Description :

import _thread as thread
import base64
import hashlib
import hmac
import json
import random
import ssl
import threading
import time
import traceback

import websocket
from django.conf import settings
from requests_toolbelt.multipart.encoder import MultipartEncoder


class DocumentUpload:
    def __init__(self, timestamp):
        self.APPId = settings.SPARK_KNOWLEDGE_BASE_APP_ID
        self.APISecret = settings.SPARK_KNOWLEDGE_BASE_APP_SECRET
        self.Timestamp = timestamp

    def get_origin_signature(self):
        data = (self.APPId + self.Timestamp).encode("utf-8")
        checkSum = hashlib.md5(data).hexdigest()
        return checkSum

    def get_signature(self):
        signature_origin = self.get_origin_signature()
        signature = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha1,
        ).digest()
        signature = base64.b64encode(signature).decode("utf-8")
        return signature

    def get_header(self):
        return {
            "appId": self.APPId,
            "timestamp": self.Timestamp,
            "signature": self.get_signature(),
        }

    def get_body(self, url, file_name):
        body = {
            "file": "",
            "url": url,
            "fileName": file_name,
            "fileType": "wiki",
            "callbackUrl": "your_callbackUrl",
        }
        boundary = "------------------" + str(random.randint(1e28, 1e29 - 1))
        return MultipartEncoder(fields=body, boundary=boundary)

    def get_files_and_body(self):
        return {"file": open("file.txt", "rb")}, {
            "url": "",
            "fileName": "file.txt",
            "fileType": "wiki",
            "needSummary": False,
            "stepByStep": False,
            "callbackUrl": "your_callbackUrl",
        }


class SparkQA:
    def __init__(self, TimeStamp, OriginUrl):
        self.APPId = settings.SPARK_KNOWLEDGE_BASE_APP_ID
        self.APISecret = settings.SPARK_KNOWLEDGE_BASE_APP_SECRET
        self.timeStamp = TimeStamp
        self.originUrl = OriginUrl

    def get_origin_signature(self):
        m2 = hashlib.md5()
        data = bytes(self.APPId + self.timeStamp, encoding="utf-8")
        m2.update(data)
        checkSum = m2.hexdigest()
        return checkSum

    def get_signature(self):
        # 获取原始签名
        signature_origin = self.get_origin_signature()
        # print(signature_origin)
        # 使用加密键加密文本
        signature = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha1,
        ).digest()
        # base64密文编码
        signature = base64.b64encode(signature).decode(encoding="utf-8")
        # print(signature)
        return signature

    def get_header(self):
        signature = self.get_signature()
        header = {
            "Content-Type": "application/json",
            "appId": self.APPId,
            "timestamp": self.timeStamp,
            "signature": signature,
        }
        return header

    def get_url(self):
        signature = self.get_signature()
        header = {
            "appId": self.APPId,
            "timestamp": self.timeStamp,
            "signature": signature,
        }
        return (
            self.originUrl +
            "?" +
            f"appId={self.APPId}&timestamp={self.timeStamp}&signature={signature}")
        # 使用urlencode会导致签名乱码
        # return self.originUrl + "?" + urlencode(header)

    def get_body(self, file_id, question):
        data = {
            "chatExtends": {
                "wikiPromptTpl": "请将以下内容作为已知信息：\n<wikicontent>\n请根据以上内容回答用户的问题。\n问题:<wikiquestion>\n回答:",
                "wikiFilterScore": 65,
                "temperature": 0.5,
            },
            "fileIds": [file_id],
            "messages": [{"role": "user", "content": question}],
        }
        return data


class WSComponet(object):
    @staticmethod
    # 收到websocket错误的处理
    def on_error(ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    @staticmethod
    def on_close(ws, close_status_code, close_msg):
        print("### closed ###")
        print("关闭代码：", close_status_code)
        print("关闭原因：", close_msg)

    # 收到websocket连接建立的处理
    @staticmethod
    def on_open(ws):
        thread.start_new_thread(WSComponet.run, (ws,))

    @staticmethod
    def run(ws, *args):
        data = json.dumps(ws.question)
        ws.send(data)

    # 收到websocket消息的处理
    @staticmethod
    def on_message(ws, message):
        return ws, message


class WebSocketHandler:
    def __init__(self, url, body):
        self.url = url
        self.body = body
        self.message = None
        self.error = None
        self.event = threading.Event()

    def on_message(self, ws, message):
        self.message = message
        self.event.set()

    def on_error(self, ws, error):
        self.error = error
        self.event.set()
        ws.close()

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")

    def on_open(self, ws):
        ws.send(self.body)

    def run(self):
        try:
            websocket.enableTrace(True)
            ws = websocket.WebSocketApp(
                self.url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open,
            )

            thread = threading.Thread(
                target=ws.run_forever, kwargs={
                    "sslopt": {
                        "cert_reqs": ssl.CERT_NONE}})
            thread.start()
            self.event.wait()
            ws.close()
            if self.error:
                print("Error:", self.error)
                return None
            return self.message
        except Exception:
            print(traceback.format_exc())
