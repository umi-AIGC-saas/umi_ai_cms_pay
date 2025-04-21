"""
@Author				: XiaoTao
@Email				: 18773993654@163.com
@Lost modifid		: 2023/4/24 17:24
@Filename			: language_pack.py
@Description		:
@Software           : PyCharm
"""


class RET:
    """
    语言类包
    """

    OK = 20000
    SERVER_ERROR = 50000
    DB_ERR = 50001
    ORDER_CREATE_ERR = 30001
    ALIPAY_PAY_QR_FAIL = 30002
    WECHAT_PAY_QR_FAIL = 30003
    WECHAT_PAY_CALLBACK_FAIL = 30004
    ALIPAY_PAY_CALLBACK_FAIL = 30005
    ORDER_AMOUNT_ERR = 30006
    PAY_RES_ERR = 30007
    PAY_SUCCESS = 30008
    PRE_PAY = 30009
    DECO_GOT = 30010
    ORDER_EXPIRED = 30011
    NOT_YOUR_ORDER = 30012
    NO_SUCH_USER = 30013
    VIP_EXPIRED = 30014
    STREAM_LIMITED = 30015
    USER_ABNORMAL = 30016
    CODE_EXPIRED = 30017
    CODE_INVALID = 30018
    CODE_CONSUMED = 30019
    ALREADY_VIP = 30020
    TEST = 30021
    REJECT = 30022
    PACKAGE_UNAVLIABLE = 30023
    USED_UP = 40022
    NOT_VIP = 30025
    NETWORK_ERROR = 30026
    NO_PRODUCT_FOUND = 30027
    PARAM_MISSING = 30028
    DATA_NOT_FOUND = 30029
    CHARACTER_DUPLICATE = 30030
    ERROR_CHANGE_TUTOR = 30031
    UNSUPPORTED_FILE = 30032
    ERROR_CONSUME_HASHRATE = 30033
    SOUND_NOT_CLEAR = 30034
    GROUP_DUPLICATE = 30035


# 元组中第一个为中文，第二个为英文，第三个为繁体
language_pack = {
    RET.OK: ("成功",),
    RET.SERVER_ERROR: ("服务器异常",),
    RET.DB_ERR: ("数据库异常",),
    RET.ORDER_CREATE_ERR: ("订单生成失败",),
    RET.WECHAT_PAY_QR_FAIL: ("微信支付二维码生成失败",),
    RET.ALIPAY_PAY_QR_FAIL: ("支付宝二维码生成失败",),
    RET.ALIPAY_PAY_CALLBACK_FAIL: ("支付宝回调失败",),
    RET.WECHAT_PAY_CALLBACK_FAIL: ("微信支付回调失败",),
    RET.ORDER_AMOUNT_ERR: ("订单总金额有误",),
    RET.PAY_RES_ERR: ("支付结果查询",),
    RET.PAY_SUCCESS: ("支付成功",),
    RET.PRE_PAY: ("待付款",),
    RET.ORDER_EXPIRED: ("订单过期",),
    RET.DECO_GOT: ("链路追踪捕获",),
    RET.NOT_YOUR_ORDER: ("非本人订单",),
    RET.NO_SUCH_USER: ("当前用户无记录",),
    RET.VIP_EXPIRED: ("会员过期",),
    RET.STREAM_LIMITED: ("您已触发限流",),
    RET.USER_ABNORMAL: ("用户当前状态异常",),
    RET.CODE_EXPIRED: ("卡密过期",),
    RET.CODE_INVALID: ("卡密无效",),
    RET.CODE_CONSUMED: ("卡密被使用",),
    RET.ALREADY_VIP: ("已经是会员",),
    RET.TEST: ("测试错误",),
    RET.REJECT: ("每位用户只能购买一次体验卡",),
    RET.PACKAGE_UNAVLIABLE: ("当前未购买加油包",),
    RET.USED_UP: ("加油包余量不足",),
    RET.NOT_VIP: ("当前非会员",),
    RET.NETWORK_ERROR: ("网络异常",),
    RET.NO_PRODUCT_FOUND: ("未找到该产品",),
    RET.PARAM_MISSING: ("参数缺失",),
    RET.DATA_NOT_FOUND: ("没有对应数据",),
    RET.CHARACTER_DUPLICATE: ("已添加过同名导师",),
    RET.ERROR_CHANGE_TUTOR: ("更换导师异常",),
    RET.UNSUPPORTED_FILE: ("不支持的文档格式",),
    RET.ERROR_CONSUME_HASHRATE: ("扣费失败,请留意算力余额",),
    RET.SOUND_NOT_CLEAR: ("声音文件不清晰",),
    RET.GROUP_DUPLICATE: ("已经有相同分组了",),
}


class Language(object):
    _lang = "zh_cn"

    @classmethod
    def init(cls, lang):
        cls._lang = lang

    @classmethod
    def get(cls, value):
        lang = language_pack.get(value)
        if not lang:
            return None
        if cls._lang == "zh_cn" and len(lang) > 0:
            return lang[0]
        elif cls._lang == "en_US" and len(lang) > 1:
            return lang[1]
        elif cls._lang == "zh_F" and len(lang) > 2:
            return lang[2]
