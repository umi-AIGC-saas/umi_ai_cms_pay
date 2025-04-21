from typing import Any

from knowledge_base.embedchain.pipeline import Pipeline as App
from knowledge_base.embedchain.config import AddConfig, BaseLlmConfig, PipelineConfig
from knowledge_base.embedchain.embedder.openai import OpenAIEmbedder
from knowledge_base.embedchain.helpers.json_serializable import (JSONSerializable,
                                                  register_deserializable)
from knowledge_base.embedchain.llm.openai import OpenAILlm
from knowledge_base.embedchain.vectordb.chroma import ChromaDB


@register_deserializable
class BaseBot(JSONSerializable):
    def __init__(self):
        self.app = App(config=PipelineConfig(), llm=OpenAILlm(), db=ChromaDB(), embedding_model=OpenAIEmbedder())

    def add(self, data: Any, config: AddConfig = None):
        """
        Add data to the bot (to the vector database).
        Auto-dectects type only, so some data types might not be usable.

        :param data: data to embed
        :type data: Any
        :param config: configuration class instance, defaults to None
        :type config: AddConfig, optional
        """
        config = config if config else AddConfig()
        self.app.add(data, config=config)

    def query(self, query: str, config: BaseLlmConfig = None) -> str:
        """
        Query the bot

        :param query: the user query
        :type query: str
        :param config: configuration class instance, defaults to None
        :type config: BaseLlmConfig, optional
        :return: Answer
        :rtype: str
        """
        config = config
        return self.app.query(query, config=config)

    def start(self):
        """Start the bot's functionality."""
        raise NotImplementedError("Subclasses must implement the start method.")
