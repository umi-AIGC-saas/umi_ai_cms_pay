"""
URL configuration for server_pay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions


class CustomSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        # 获取所有的路径
        paths = schema["paths"]

        # print(paths.items())
        # 对路径进行排序，将指定接口的路径放在前面
        sorted_paths = sorted(paths.items(),
                              key=lambda x: x[0] != "/your/api/path")

        # 重新设置排序后的路径
        schema["paths"] = dict(sorted_paths)

        return schema


schema_view = get_schema_view(
    openapi.Info(
        title="ChatAI Pay Module Document",
        default_version="v1",
        description="API documentation for the ChatAI Pay module",
        contact=openapi.Contact(email="payne6861@outlook.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    generator_class=CustomSchemaGenerator,  # 使用自定义的 SchemaGenerator
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path(
        "docs/",
        schema_view.with_ui(
            "swagger",
            cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui(
            "redoc",
            cache_timeout=0),
        name="schema-redoc"),
    path(
        "admin/",
        admin.site.urls),
    path(
        "pay/",
        include("apps.sp_pay.urls")),
    path(
        "assistant/",
        include("apps.sva_virtual_assistant.urls")),
    path(
        "kb/",
        include("apps.skb_knowledge_base.urls")),
    path(
        "speech/",
        include("apps.s_speech.urls")),
    path(
        "agent/",
        include("apps.ap_agent.urls")),
]
