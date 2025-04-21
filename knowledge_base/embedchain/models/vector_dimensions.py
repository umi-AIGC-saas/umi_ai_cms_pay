from enum import Enum


# vector length created by embedding fn
class VectorDimensions(Enum):
    GPT4ALL = 384
    OPENAI = 1536
    VERTEX_AI = 768
    #TODO 测试改为1024
    HUGGING_FACE = 384
    # HUGGING_FACE = 1024
    GOOGLE_AI = 768
