import os

import pytest

import embedchain
import embedder.gpt4all
import embedder.huggingface
import embedder.openai
import embedder.vertexai
import llm.anthropic
import llm.openai
import vectordb.chroma
import vectordb.elasticsearch
import vectordb.opensearch
from factory import EmbedderFactory, LlmFactory, VectorDBFactory


class TestFactories:
    @pytest.mark.parametrize(
        "provider_name, config_data, expected_class",
        [
            ("openai", {}, llm.openai.OpenAILlm),
            ("anthropic", {}, llm.anthropic.AnthropicLlm),
        ],
    )
    def test_llm_factory_create(self, provider_name, config_data, expected_class):
        os.environ["ANTHROPIC_API_KEY"] = "test_api_key"
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        llm_instance = LlmFactory.create(provider_name, config_data)
        assert isinstance(llm_instance, expected_class)

    @pytest.mark.parametrize(
        "provider_name, config_data, expected_class",
        [
            ("gpt4all", {}, embedder.gpt4all.GPT4AllEmbedder),
            (
                "huggingface",
                {"model": "sentence-transformers/all-mpnet-base-v2"},
                embedder.huggingface.HuggingFaceEmbedder,
            ),
            ("vertexai", {"model": "textembedding-gecko"}, embedder.vertexai.VertexAIEmbedder),
            ("openai", {}, embedder.openai.OpenAIEmbedder),
        ],
    )
    def test_embedder_factory_create(self, mocker, provider_name, config_data, expected_class):
        mocker.patch("embedder.vertexai.VertexAIEmbedder", autospec=True)
        embedder_instance = EmbedderFactory.create(provider_name, config_data)
        assert isinstance(embedder_instance, expected_class)

    @pytest.mark.parametrize(
        "provider_name, config_data, expected_class",
        [
            ("chroma", {}, vectordb.chroma.ChromaDB),
            (
                "opensearch",
                {"opensearch_url": "http://localhost:9200", "http_auth": ("admin", "admin")},
                vectordb.opensearch.OpenSearchDB,
            ),
            ("elasticsearch", {"es_url": "http://localhost:9200"}, vectordb.elasticsearch.ElasticsearchDB),
        ],
    )
    def test_vectordb_factory_create(self, mocker, provider_name, config_data, expected_class):
        mocker.patch("vectordb.opensearch.OpenSearchDB", autospec=True)
        vectordb_instance = VectorDBFactory.create(provider_name, config_data)
        assert isinstance(vectordb_instance, expected_class)
