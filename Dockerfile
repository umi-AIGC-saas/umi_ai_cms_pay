# 第一阶段：构建依赖项镜像
FROM python:3.11-slim-buster AS builder

## 修改 apt 源
# RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
#    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

ADD ./sources.list /etc/apt/

# 修改 python 源
RUN echo "[global]\n\
index-url = https://pypi.tuna.tsinghua.edu.cn/simple\n\
\n\
[install]\n\
trusted-host=mirrors.aliyun.com\n\
           mirrors.aliyuncs.com\n\
           pypi.tuna.tsinghua.edu.cn\n\
           pypi.doubanio.com\n\
           pypi.python.org" > /etc/pip.conf

# 设置工作目录
WORKDIR /usr/src/app

# 复制 requirements.txt 文件
COPY requirements.txt .
COPY pysqlite3_binary-0.5.2-cp311-cp311-manylinux_2_24_x86_64.whl .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential  \
        libpq5 \
        sqlite3 \
        tzdata && \
    rm -rf /var/lib/apt/lists/*


# 安装依赖项
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install pysqlite3_binary-0.5.2-cp311-cp311-manylinux_2_24_x86_64.whl  && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# 第二阶段：构建应用程序镜像
FROM python:3.11-slim-buster

# 修改 apt 源
#RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
#    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
ADD ./sources.list /etc/apt/

# 修改 python 源
RUN echo "[global]\n\
index-url = https://pypi.tuna.tsinghua.edu.cn/simple\n\
\n\
[install]\n\
trusted-host=mirrors.aliyun.com\n\
           mirrors.aliyuncs.com\n\
           pypi.tuna.tsinghua.edu.cn\n\
           pypi.doubanio.com\n\
           pypi.python.org" > /etc/pip.conf

# 安装所需的运行时库
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential  \
        libpq5 \
        sqlite3 \
        tzdata && \
    rm -rf /var/lib/apt/lists/* \

# 设置工作目录并复制依赖项
WORKDIR /usr/src/app
COPY --from=builder /install /usr/local

# 复制应用程序代码
COPY .. .

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/usr/src/app:$PATH

EXPOSE 8082

# 配置 Gunicorn
# CMD ["gunicorn", "server_pay.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8888", "--workers=$(python -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')"]
