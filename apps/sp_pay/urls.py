#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/26 11:53
# @Author  : payne
# @File    : urls.py
# @Description : pay 模块路由


from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.ProductsList.as_view(), name="获取产品列表"),
    path("orders/", views.OrdersList.as_view(), name="获取订单列表"),
    path("members_manage/", views.MembershipManage.as_view(), name="获取会员信息列表"),
    path("new_visitor/", views.NewVisitorUser.as_view(), name="管理新的访客"),
    path("form_sheet_alipay/", views.FormSheetAlipay.as_view(), name="构造支付宝支付请求"),
    path("update_order_alipay/", views.UpdateOrderAlipay.as_view(), name="支付宝支付回调"),
    path("query_status_alipay/", views.QueryOrderStatus.as_view(), name="查询订单支付状态"),
    path("form_sheet_wechat/", views.FormSheetWechat.as_view(), name="构造微信支付请求"),
    path(
        "form_sheet_wechat_mp/",
        views.FormSheetWechatMiniProgram.as_view(),
        name="构造微信支付请求",
    ),
    path("form_sheet_wechat_h5/", views.FormSheetWechatH5.as_view(), name="构造微信支付请求"),
    path("update_order_wechat/", views.UpdateOrderWechat.as_view(), name="微信支付回调"),
    path("query_status_wechat/", views.QueryStatusWechat.as_view(), name="微信查询订单支付状态"),
    path("activate_code_consume/", views.ActivateCodeConsume.as_view(), name="卡密核销"),
    path("pay_result/", views.PayResult.as_view(), name="同步查询支付结果"),
    path("tokens/", views.Tokens.as_view(), name="获取当前用户token和次数【已废弃】"),
    path("intro/", views.Introduction.as_view(), name="文档相关参数说明"),
    path("contact/", views.BusinessCooperation.as_view(), name="商业合作"),
    path("pictures/", views.PicturesManage.as_view(), name="图片管理"),
    path("repay/", views.RePay.as_view(), name="重新发起支付"),
    path("token_init/", views.UserCountInit.as_view(), name="用户token初始化"),
    path("token_manage/", views.UserCountManage.as_view(), name="管理用户token"),
    path(
        "token_manage_redis/",
        views.UserCountManageRedis.as_view(),
        name="管理用户token Redis",
    ),
    path(
        "token_manage_redis_no_vip/",
        views.UserCountManageRedisNoVip.as_view(),
        name="管理用户token Redis 非vip",
    ),
    path("questions_set/", views.QuestionsSetManage.as_view(), name="问题集"),
    path("questions_set_search/", views.QuestionsSetSearch.as_view(), name="问题集"),
    path("tab/", views.TabManage.as_view(), name="tab栏"),
    path("industry/", views.IndustryManage.as_view(), name="行业"),
    path("occupation/", views.OccupationManage.as_view(), name="职业"),
    path("sec_occupation/", views.SubOccupationManage.as_view(), name="二级职业"),
    path("occu_duration/", views.EmpDurationManage.as_view(), name="从业时间"),
    path("expertise_level/", views.ExpertiseLevelManage.as_view(), name="职业技能等级"),
    path("modules/", views.OpModulesManage.as_view(), name="对应模块"),
    path("token_consume/", views.TokenConsume.as_view(), name="token 消费"),
    path(
        "token_consume_universal/",
        views.TokenConsumeUniversal.as_view(),
        name="token 消费 通用流量包",
    ),
    path("traffic_control/", views.TrafficControlRouter.as_view(), name="流量包/会员次数判断"),
    path("message_center/", views.OmtMessageCenterManage.as_view(), name="消息中心获"),
    path(
        "message_center_content/",
        views.OmtMessageCenterContentManage.as_view(),
        name="消息中心获",
    ),
    path("billing_center/", views.BillingCenter.as_view(), name="计费中心"),
    path("question_set_recommend/", views.QeustionSetRecommend.as_view(), name="问题集推荐"),
    path("drawing_set_recommend/", views.DrawingSetRecommend.as_view(), name="绘图集集推荐"),
    path("question_config/", views.QuestionsSetEditView.as_view(), name="问题集编辑配置项"),
    path("get_total_amount/", views.GetOutputVideoData.as_view(), name="获取输出视频总价和市场"),
]
