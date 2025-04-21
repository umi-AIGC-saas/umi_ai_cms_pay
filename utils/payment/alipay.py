# -*- coding: utf-8 -*-
"""
Date :
Author :
Desc :
"""
import json
import logging
from base64 import decodebytes, encodebytes
from datetime import datetime
from urllib.parse import quote_plus
from urllib.request import urlopen

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from config import *
from utils.exception import AliPayException, AliPayValidationError

logger = logging.getLogger("views")


class AliPay(object):
    """
    支付宝支付接口
    """

    def __init__(self, debug=False):
        self.appid = app_id
        self.app_notify_url = app_notify_url

        self.return_url = return_url

        with open(app_private_key_path) as fp:
            self.app_private_key = RSA.importKey(fp.read())
        with open(alipay_public_key_path) as fp:
            self.alipay_public_key = RSA.importKey(fp.read())

        # if debug is True:
        #     self.__gateway = "https://openapi.alipaydev.com/gateway.do"
        # else:
        self.__gateway = "https://openapi.alipay.com/gateway.do"

    def direct_pay(
        self, subject, out_trade_no, total_amount, return_url=None, **kwargs
    ):
        biz_content = {
            "subject": subject,
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            # "qr_pay_mode":4
        }
        print(self.app_notify_url)
        biz_content.update(kwargs)
        data = self.build_body(
            "alipay.trade.page.pay",
            biz_content,
            self.return_url)
        return self.sign_data(data)

    def h5_pay(
            self,
            subject,
            out_trade_no,
            total_amount,
            return_url=None,
            **kwargs):
        biz_content = {
            "subject": subject,
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            # "qr_pay_mode":4
        }

        biz_content.update(kwargs)
        data = self.build_body(
            "alipay.trade.wap.pay",
            biz_content,
            self.return_url)
        return self.sign_data(data)

    def app_pay(
            self,
            subject,
            out_trade_no,
            total_amount,
            return_url=None,
            **kwargs):
        biz_content = {
            "subject": subject,
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "product_code": "QUICK_MSECURITY_PAY",
            # "qr_pay_mode":4
        }

        biz_content.update(kwargs)
        data = self.build_body(
            "alipay.trade.app.pay",
            biz_content,
            self.return_url)
        return self.sign_data(data)

    def api_alipay_trade_query(self, out_trade_no=None, trade_no=None):
        """
        response = {
            "alipay_trade_query_response": {
                "trade_no": "2017032121001004070200176844",
                "code": "10000",
                "invoice_amount": "20.00",
                "open_id": "20880072506750308812798160715407",
                "fund_bill_list": [
                    {
                        "amount": "20.00",
                        "fund_channel": "ALIPAYACCOUNT"
                    }
                ],
                "buyer_logon_id": "csq***@sandbox.com",
                "send_pay_date": "2017-03-21 13:29:17",
                "receipt_amount": "20.00",
                "out_trade_no": "out_trade_no15",
                "buyer_pay_amount": "20.00",
                "buyer_user_id": "2088102169481075",
                "msg": "Success",
                "point_amount": "0.00",
                "trade_status": "TRADE_SUCCESS",
                "total_amount": "20.00"
            },
            "sign": ""
        }
        """
        assert (out_trade_no is not None) or (
            trade_no is not None
        ), "Both trade_no and out_trade_no are None"

        biz_content = {}
        if out_trade_no:
            biz_content["out_trade_no"] = out_trade_no
        if trade_no:
            biz_content["trade_no"] = trade_no
        data = self.build_body("alipay.trade.query", biz_content)
        response_type = "alipay_trade_query_response"
        return self.verified_sync_response(data, response_type)

    def verified_sync_response(self, data, response_type):
        url = self.__gateway + "?" + self.sign_data(data)
        raw_string = urlopen(url, timeout=10).read().decode()
        return self._verify_and_return_sync_response(raw_string, response_type)

    def _verify_and_return_sync_response(self, raw_string, response_type):
        """
        return response if verification succeeded, raise exception if not

        As to issue #69, json.loads(raw_string)[response_type] should not be returned directly,
        use json.loads(plain_content) instead

        failed response is like this
        {
            "alipay_trade_query_response": {
                "sub_code": "isv.invalid-app-id",
                "code": "40002",
                "sub_msg": "无效的AppID参数",
                "msg": "Invalid Arguments"
            }
        }
        """
        response = json.loads(raw_string)
        if "sign" not in response.keys():
            result = response[response_type]

            raise AliPayException(
                code=result.get(
                    "code", "0"), message=raw_string)

        sign = response["sign"]

        # locate string to be signed
        plain_content = self._get_string_to_be_signed(
            raw_string, response_type)

        if not self._verify(plain_content, sign):
            raise AliPayValidationError
        return json.loads(plain_content)

    def _get_string_to_be_signed(self, raw_string, response_type):
        """
        https://docs.open.alipay.com/200/106120
        从同步返回的接口里面找到待签名的字符串
        """
        balance = 0
        start = end = raw_string.find("{", raw_string.find(response_type))
        # 从response_type之后的第一个｛的下一位开始匹配，
        # 如果是｛则balance加1; 如果是｝而且balance=0，就是待验签字符串的终点
        for i, c in enumerate(raw_string[start + 1:], start + 1):
            if c == "{":
                balance += 1
            elif c == "}":
                if balance == 0:
                    end = i + 1
                    break
                balance -= 1
        return raw_string[start:end]

    def build_body(self, method, biz_content, return_url=None):
        data = {
            "app_id": self.appid,
            "method": method,
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": biz_content,
        }

        if return_url is not None:
            data["notify_url"] = self.app_notify_url
            data["return_url"] = self.return_url

        return data

    def sign_data(self, data):
        data.pop("sign", None)
        # 排序后的字符串
        unsigned_items = self.ordered_data(data)
        unsigned_string = "&".join("{0}={1}".format(k, v)
                                   for k, v in unsigned_items)
        sign = self.sign(unsigned_string.encode("utf-8"))
        # ordered_items = self.ordered_data(data)
        quoted_string = "&".join(
            "{0}={1}".format(k, quote_plus(v)) for k, v in unsigned_items
        )

        # 获得最终的订单信息字符串
        signed_string = quoted_string + "&sign=" + quote_plus(sign)
        return signed_string

    def ordered_data(self, data):
        complex_keys = []
        for key, value in data.items():
            if isinstance(value, dict):
                complex_keys.append(key)

        # 将字典类型的数据dump出来
        for key in complex_keys:
            data[key] = json.dumps(data[key], separators=(",", ":"))

        return sorted([(k, v) for k, v in data.items()])

    def sign(self, unsigned_string):
        # 开始计算签名
        key = self.app_private_key

        signer = PKCS1_v1_5.new(key)
        logger.info(unsigned_string)
        signature = signer.sign(SHA256.new(unsigned_string))

        # base64 编码，转换为unicode表示并移除回车
        sign = encodebytes(signature).decode("utf8").replace("\n", "")
        return sign

    def _verify(self, raw_content, signature):
        # 开始计算签名
        key = self.alipay_public_key
        signer = PKCS1_v1_5.new(key)
        digest = SHA256.new()
        digest.update(raw_content.encode("utf8"))

        if signer.verify(digest, decodebytes(signature.encode("utf8"))):
            return True
        return False

    def verify(self, data, signature):
        if "sign_type" in data:
            sign_type = data.pop("sign_type")
        # 排序后的字符串
        unsigned_items = self.ordered_data(data)
        message = "&".join("{}={}".format(k, v) for k, v in unsigned_items)
        return self._verify(message, signature)

    # def web_pay(self):
    #     order_string = alipay.api_alipay_trade_wap_pay(
    #         out_trade_no=order_sn,
    #         total_amount=str(orderObj.total_pay),
    #         subject=remark,
    #         front_url=front_url
    #     )
