# # -*- coding: utf-8 -*-
# """
# Date : 20201103
# Author : panxi
# Desc : 微信支付配置
# """
import hashlib
import logging
import time
from random import Random

import requests
from django.conf import settings
from django.http import HttpResponse
from oss2.utils import AESCipher

# from config import *
# from config_chat import *
# from config_dev import *
# from config_chat_dev import *
from config import *
# from config_umi_dev import *

from language.language_pack import RET
from utils.cst_class import CstException

logger = logging.getLogger("views")


def random_str(randomlength=8):
    """
    生成随机字符串
    :param randomlength: 字符串长度
    :return:
    """
    strs = ""
    chars = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789"
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        strs += chars[random.randint(0, length)]
    return strs


# 请求统一支付接口
def wxpay(
    order_id,
    order_name,
    order_price_detail,
    order_total_price,
    trade_type,
    open_id="",
    app_id=APP_ID,
):
    nonce_str = random_str()  # 拼接出随机的字符串即可，我这里是用  时间+随机数字+5个随机字母
    total_fee = int(float(order_total_price) * 100)  # 付款金额，单位是分，必须是整数
    params = {
        "appid": app_id,  # APPID
        "mch_id": MCH_ID,  # 商户号
        "nonce_str": nonce_str,  # 随机字符串
        "out_trade_no": order_id,  # 订单编号，可自定义
        "total_fee": total_fee,  # 订单总金额
        "spbill_create_ip": CREATE_IP,  # 自己服务器的IP地址
        "notify_url": NOTIFY_URL,  # 回调地址，微信支付成功后会回调这个url，告知商户支付结果
        "body": order_name,  # 商品描述
        "detail": order_price_detail,  # 商品描述
        "trade_type": trade_type,  # 扫码支付类型
    }

    # JSAPI 和 MWEB下需要传入open_id, 根据前端传来的code通过接口获取
    if trade_type not in ["NATIVE", "MWEB"]:
        params["openid"] = open_id

    print(f"wx_pay 调用参数 {params}")
    sign = get_sign(params, API_KEY)  # 获取签名
    params["sign"] = sign  # 添加签名到参数字典
    xml = trans_dict_to_xml(params)  # 转换字典为XML
    response = requests.request(
        "post", UFDODER_URL, data=xml.encode()
    )  # 以POST方式向微信公众平台服务器发起请求
    data_dict = trans_xml_to_dict(response.content)  # 将请求返回的数据转为字典
    return data_dict


def get_sign(data_dict, key):
    """
    签名函数
    :param data_dict: 需要签名的参数，格式为字典
    :param key: 密钥 ，即上面的API_KEY
    :return: 字符串
    """
    params_list = sorted(
        data_dict.items(), key=lambda e: e[0], reverse=False
    )  # 参数字典倒排序为列表
    params_str = "&".join("{}={}".format(k, v)
                          for k, v in params_list) + "&key=" + key
    # 组织参数字符串并在末尾添加商户交易密钥
    md5 = hashlib.md5()  # 使用MD5加密模式
    md5.update(params_str.encode("utf-8"))  # 将参数字符串传入
    sign = md5.hexdigest().upper()  # 完成加密并转为大写
    return sign


def trans_dict_to_xml(data_dict):
    """
    定义字典转XML的函数
    :param data_dict:
    :return:
    """
    data_xml = []
    for k in sorted(data_dict.keys()):  # 遍历字典排序后的key
        v = data_dict.get(k)  # 取出字典中key对应的value
        if k == "detail" and not v.startswith("<![CDATA["):  # 添加XML标记
            v = "<![CDATA[{}]]>".format(v)
        data_xml.append("<{key}>{value}</{key}>".format(key=k, value=v))
    return "<xml>{}</xml>".format("".join(data_xml))  # 返回XML


def trans_xml_to_dict(data_xml):
    """
    定义XML转字典的函数
    :param data_xml:
    :return:
    """
    data_dict = {}
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET
    root = ET.fromstring(data_xml)
    for child in root:
        data_dict[child.tag] = child.text
    return data_dict


def get_openid(code):
    """小程序获取openid"""
    params = {
        "appid": MINI_PROGRAM_APP_ID,
        "secret": MINI_PROGRAM_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    logger.info(f"open_id params {params}")
    res = requests.get(settings.XCX_AUTH, params=params)
    if res.status_code == requests.codes.ok:
        res = res.json()
        openid = res.get("openid")
        if res.get("errcode") == 40029:
            raise CstException(RET.WECHAT_PAY_QR_FAIL)
        if not openid:
            raise CstException(RET.WECHAT_PAY_QR_FAIL, res)
        return openid
    raise CstException(RET.WECHAT_PAY_QR_FAIL, "获取openid异常")


def get_jsapi_openid(code, appid, secret):
    """h5获取openid"""
    params = {
        "appid": appid,
        "secret": secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    res = requests.get(settings.MWEB_AUTH, params=params)
    if res.status_code == requests.codes.ok:
        res = res.json()
        openid = res.get("openid")
        if res.get("errcode") == 40029:
            raise CstException(RET.WECHAT_PAY_QR_FAIL)
        if not openid:
            raise CstException(RET.WECHAT_PAY_QR_FAIL, res)
        return openid
    raise CstException(RET.WECHAT_PAY_QR_FAIL, "获取openid异常")


def get_pay_sign(data_dict, source):
    if data_dict.get("return_code") == "SUCCESS":

        if source == "xcx_wcxt":
            app_id = settings.WC_MINI_PROGRAM_APP_ID
        elif source == "umi_h5":
            app_id = settings.APP_ID
        elif source == "xcx":
            app_id = settings.ZN_MINI_PROGRAM_APP_ID
        else:
            app_id = settings.MINI_PROGRAM_APP_ID

        if data_dict.get("result_code") == "SUCCESS":
            prepay_id = data_dict.get("prepay_id")
            timeStamp = str(int(time.time()))

            data = {
                "appId": app_id,
                "nonceStr": random_str(),
                "package": "prepay_id=" + prepay_id,
                "signType": "MD5",
                "timeStamp": timeStamp,
            }
            paySign = get_sign(data, settings.API_KEY)

            ret_data = {
                "app_id": data["appId"],
                "nonce_str": data["nonceStr"],
                "package": data["package"],
                "sign_type": data["signType"],
                "time_stamp": data["timeStamp"],
                "pay_sign": paySign,
                "mweb_url": data_dict.get("mweb_url"),
            }

            return ret_data


def query_payment_status(order_id, source):
    if not order_id:
        return False

    nonce_str = random_str()

    if source == "xcx_wcxt":
        app_id = settings.WC_MINI_PROGRAM_APP_ID
    elif source == "umi_h5":
        app_id = settings.APP_ID

    else:
        app_id = settings.MINI_PROGRAM_APP_ID

    params = {
        "appid": app_id,  # APPID
        "mch_id": MCH_ID,  # 商户号
        "nonce_str": nonce_str,  # 随机字符串
        "sign_type": "MD5",
        "out_trade_no": str(order_id),  # 订单编号
    }

    sign = get_sign(params, API_KEY)  # 获取签名
    params["sign"] = sign  # 添加签名到参数字典
    xml = trans_dict_to_xml(params)  # 转换字典为XM

    print(f"query wechat payment {xml}")

    response = requests.request(
        "post", QUERY_URL, data=xml.encode()
    )  # 以POST方式向微信公众平台服务器发起请求
    data_dict = trans_xml_to_dict(response.content)  # 将请求返回的数据转为字典

    print(data_dict)
    if data_dict.get("return_code") == "SUCCESS":
        return data_dict
    else:
        return ""


# class OrderRefund(APIView):
#     """微信支付退款"""
#
#     def get(self, request):
#         """退款查询"""
#         data = request.query_params
#         out_refund_no = data.get("out_refund_no")
#         if not out_refund_no:
#             return CstResponse(RET.PARAMERR)
#         wx_pay = SpOrderWxpay.objects.filter(order_id=out_refund_no).first()
#         if not wx_pay:
#             return CstResponse(RET.NET_ERR, Language.get("order_orr"))
#         nonce_str = random_str()
#         params = {
#             'appid': settings.APP_ID,  # APPID
#             'mch_id': settings.MCH_ID,  # 商户号
#             'nonce_str': nonce_str,  # 随机数
#             'sign_type': 'MD5',
#             "out_refund_no": str(out_refund_no) + wx_pay.order_suffix,
#             # "refund_id": "",        # 微信生成的退款单号，在申请退款接口有返回
#         }
#         data_dict = wx_pay_help(params, settings.REFUND_QUERY_URL, settings.KEY)
#         if data_dict.get('return_code') == 'SUCCESS':
#             if data_dict.get("err_code") in ["SYSTEMERROR", "REFUNDNOTEXIST", "INVALID_TRANSACTIONID", "PARAM_ERROR",
#                                              "SIGNERROR", "XML_FORMAT_ERROR", "APPID_NOT_EXIST", "MCHID_NOT_EXIST",
#                                              "REQUIRE_POST_METHOD"]:
#                 return CstResponse(RET.DATA_ERR, data={"err_code": data_dict.get("err_code"),
#                                                        "err_code_des": data_dict.get("err_code_des")})
#             else:
#                 data_dict = data_dict_pop(data_dict)
#                 return CstResponse(RET.OK, data=data_dict)
#         else:
#             return CstResponse(RET.DATA_ERR)
#
#     def post(self, request):
#         data = request.data
#         data = sign_check(data)
#         out_trade_no = data.get("out_trade_no")
#         total_fee = data.get("total_fee")
#         refund_fee = data.get("refund_amount")
#         out_refund_no = data.get("out_refund_no", None)
#         if not all([out_trade_no, total_fee, refund_fee]):
#             return CstResponse(RET.PARAMERR)
#         if not out_refund_no:
#             out_refund_no = out_trade_no
#
#         wx_pay = SpOrderWxpay.objects.filter(order_id=out_trade_no).first()
#         if not wx_pay:
#             return CstResponse(RET.NET_ERR, Language.get("order_orr"))
#         if refund_fee < "0":
#             return CstResponse(RET.PARAMERR, Language.get("pay_err"))
#         nonce_str = random_str()
#         params = {
#             'appid': settings.APP_ID,
#             'mch_id': settings.MCH_ID,
#             'nonce_str': nonce_str,
#             'sign_type': 'MD5',
#             'out_trade_no': str(out_trade_no) + wx_pay.order_suffix,  # 订单编号
#             "out_refund_no": out_refund_no,  # 退款单号，多笔退款时使用
#             "total_fee": total_fee,  # 订单金额
#             "refund_fee": refund_fee,  # 退款金额
#             "notify_url": settings.RETURN_URL + "/api/server_pay/wxpay/mweb/refund/notice"
#         }
#         sign = get_sign(params, settings.KEY)
#         params['sign'] = sign
#         xml = trans_dict_to_xml(params)
#
#         response = requests.post(settings.REFUND_URL, data=xml.encode('utf8'), cert=(SP_WXPAY_CERT_PC, SP_WXPAY_KEY_PC),
#                                  verify=True)
#         data_dict = trans_xml_to_dict(response.content)
#         if data_dict.get('return_code') == 'SUCCESS':
#             data_dict = data_dict_pop(data_dict)
#             if wx_pay:
#                 wx_pay.refund_amount += int(refund_fee)
#                 wx_pay.refund_times += 1
#                 wx_pay.save()
#             return CstResponse(RET.OK, data=data_dict)
#         else:
#             return CstResponse(RET.PAY_REFUND)


# class RefundNoticeMWEB(APIView):
#     """微信退款回调"""
#
#     def post(self, request):
#         data = request.body
#         data_dict = trans_xml_to_dict(data)  # 回调数据转字典
#         if data_dict.get('return_code') == 'SUCCESS':
#             req_info = data_dict.get("req_info")
#             if not req_info:
#                 return HttpResponse("""<xml>
#                                               <return_code><![CDATA[FAIL]]></return_code>
#                                               <return_msg><![CDATA[SIGNERROR]]></return_msg>
#                                             </xml>""", content_type="application/xml")
#             refund_pay_info = AESCipher(settings.KEY).decrypt(req_info)
#             refund_pay_info = trans_xml_to_dict(b"<xml>" + refund_pay_info + b"</xml>")
#             out_trade_no = refund_pay_info.get("out_trade_no")  # 订单号
#             wx_pay = SpOrderWxpay.objects.filter(order_id=out_trade_no).first()
#             refund_status = refund_pay_info.get("refund_status")
#             if refund_status == "SUCCESS":
#                 if refund_pay_info.get("out_trade_no"):
#                     refund_pay_info["out_trade_no"] = refund_pay_info.get("out_trade_no")[:-6]
#                 url = settings.WX_REFUND_NOTICE_URL + "/api/server_order/order/refund/logistics_callback"  #
#                 refund_pay_info["sign"] = get_sign(refund_pay_info, settings.KEY)
#                 res = requests.post(url, json={"req_info": refund_pay_info, "pay_type": "WX"})
#                 if res.status_code == 200 and res.json().get("code") == 200:
#                     if wx_pay:
#                         wx_pay.refund_amount += int(refund_pay_info.get("settlement_refund_fee"))
#                         wx_pay.refund_times += 1
#                         wx_pay.save()
#                     return HttpResponse("""<xml>
#                                                       <return_code><![CDATA[SUCCESS]]></return_code>
#                                                       <return_msg><![CDATA[OK]]></return_msg>
#                                                     </xml>""", content_type="application/xml")
#         return HttpResponse("""<xml>
#                                       <return_code><![CDATA[FAIL]]></return_code>
#                                       <return_msg><![CDATA[SIGNERROR]]></return_msg>
#                                     </xml>""", content_type="application/xml")
