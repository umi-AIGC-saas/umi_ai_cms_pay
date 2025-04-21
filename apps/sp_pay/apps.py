from django.apps import AppConfig

# from utils.scripts.query_order_status import QueryOrderStatusConfig


# class SpPayConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'apps.sp_pay'
#
#     def ready(self):
#         # self.module.autodiscover()  # 自动发现应用中的管理命令
#         QueryOrderStatusConfig.ready(self)  # 启动QueryOrderStatusConfig中的脚本


class SpPayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sp_pay"
