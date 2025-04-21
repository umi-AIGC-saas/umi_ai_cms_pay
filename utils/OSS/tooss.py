# -*- coding: utf-8 -*-

import oss2
import requests
from django.conf import settings


class Tooss(object):
    """
    阿里云OSS图片上传类
    """

    @staticmethod
    def uploadToOss(
            bucket,
            imageUrl: str,
            imageName: str,
            cate,
            local,
            local_path="",
            file_obj=None):
        """
        上传图片到OSS

        :param bucket: OSS的Bucket对象
        :param imageUrl: 网络图片的URL
        :param imageName: 图片的名称
        :param cate: 分类
        :param local: 是否是本地图片
        :param local_path: 本地图片的路径
        :return: 上传成功返回0，否则返回-1
        """
        objectName = cate + "/" + imageName

        # 如果是本地图片，直接读取并上传
        if local:
            try:
                with open(local_path, "rb") as fileobj:
                    bucket.put_object(objectName, fileobj)
            except Exception as e:
                print(e)
                return -1
        elif file_obj:
            # 如果是Django的 file_object ， 上传到oss
            bucket.put_object(objectName, file_obj.read())
        else:
            # 如果是网络图片，先下载，然后上传
            try:
                print(imageUrl)
                response = requests.get(imageUrl, timeout=10)
                response.raise_for_status()  # 如果请求返回的状态码不是200，将引发HTTPError异常
                bucket.put_object(objectName, response.content)
            except Exception as e:
                print("Failed to upload image: ", e)
                return -1

        return 0

    @staticmethod
    def main(imgUrl, cate, name, local=False, local_path="", file_obj=None):
        """
        主函数，创建Bucket对象，并调用uploadToOss函数上传图片

        :param imgUrl: 图片的URL
        :param cate: 分类
        :param local: 是否是本地图片
        :param local_path: 本地图片的路径
        :return: 上传成功返回新的URL，否则返回空字符串
        """
        # 确认上面的参数都填写正确了
        for param in (
            settings.ACCESS_KEY_ID,
            settings.ACCESS_KEY_SECRET,
            settings.BUCKET_NAME,
            settings.END_POINT,
        ):
            assert "<" not in param, "请设置参数：" + param

        # 创建Bucket对象，所有Object相关的接口都可以通过Bucket对象来进行
        bucket = oss2.Bucket(
            oss2.Auth(settings.ACCESS_KEY_ID, settings.ACCESS_KEY_SECRET),
            settings.END_POINT,
            settings.BUCKET_NAME,
        )

        iRet = Tooss.uploadToOss(
            bucket, imgUrl, name, cate, local, local_path, file_obj
        )

        if iRet != 0:
            return ""

        else:
            newUrl = settings.NETWORK_STATION + "/" + cate + "/" + name
            save_path = cate + "/" + name
            return newUrl, save_path
