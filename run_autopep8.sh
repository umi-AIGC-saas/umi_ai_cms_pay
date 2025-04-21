#!/bin/bash

# 寻找当前目录及子目录下所有的 Python 文件
# 并对每个文件执行 autopep8，同时打印文件名称
find . -type f -name "*.py" -exec sh -c 'echo "Running autopep8 on $1"; autopep8 --in-place --aggressive --aggressive $1' _ {} \;
