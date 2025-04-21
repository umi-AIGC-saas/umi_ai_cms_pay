import importlib


def load_class(class_type):
    module_path, class_name = class_type.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class LlmFactory:
    provider_to_class = {
        "anthropic": "knowledge_base.embedchain.llm.anthropic.AnthropicLlm",
        "azure_openai": "knowledge_base.embedchain.llm.azure_openai.AzureOpenAILlm",
        "cohere": "knowledge_base.embedchain.llm.cohere.CohereLlm",
        "gpt4all": "knowledge_base.embedchain.llm.gpt4all.GPT4ALLLlm",
        "ollama": "knowledge_base.embedchain.llm.ollama.OllamaLlm",
        "huggingface": "knowledge_base.embedchain.llm.huggingface.HuggingFaceLlm",
        "jina": "knowledge_base.embedchain.llm.jina.JinaLlm",
        "llama2": "knowledge_base.embedchain.llm.llama2.Llama2Llm",
        "openai": "knowledge_base.embedchain.llm.openai.OpenAILlm",
        "vertexai": "knowledge_base.embedchain.llm.vertex_ai.VertexAILlm",
        "google": "knowledge_base.embedchain.llm.google.GoogleLlm",
    }
    provider_to_config_class = {
        "embedchain": "knowledge_base.embedchain.config.llm.base.BaseLlmConfig",
        "openai": "knowledge_base.embedchain.config.llm.base.BaseLlmConfig",
        "anthropic": "knowledge_base.embedchain.config.llm.base.BaseLlmConfig",
    }

    @classmethod
    def create(cls, provider_name, config_data):
        class_type = cls.provider_to_class.get(provider_name)
        # Default to embedchain base config if the provider is not in the config map
        config_name = "embedchain" if provider_name not in cls.provider_to_config_class else provider_name
        config_class_type = cls.provider_to_config_class.get(config_name)
        if class_type:
            llm_class = load_class(class_type)
            llm_config_class = load_class(config_class_type)
            return llm_class(config=llm_config_class(**config_data))
        else:
            raise ValueError(f"Unsupported Llm provider: {provider_name}")


class EmbedderFactory:
    provider_to_class = {
        "azure_openai": "embedder.openai.OpenAIEmbedder",
        "gpt4all": "knowledge_base.embedchain.embedder.gpt4all.GPT4AllEmbedder",
        "huggingface": "embedder.huggingface.HuggingFaceEmbedder",
        "openai": "knowledge_base.embedchain.embedder.openai.OpenAIEmbedder",
        "vertexai": "embedder.vertexai.VertexAIEmbedder",
        "google": "embedder.google.GoogleAIEmbedder",
    }
    provider_to_config_class = {
        "azure_openai": "config.embedder.base.BaseEmbedderConfig",
        "openai": "knowledge_base.embedchain.config.embedder.base.BaseEmbedderConfig",
        "gpt4all": "knowledge_base.embedchain.config.embedder.base.BaseEmbedderConfig",
        "google": "config.embedder.google.GoogleAIEmbedderConfig",
    }

    @classmethod
    def create(cls, provider_name, config_data):
        class_type = cls.provider_to_class.get(provider_name)
        # Default to openai config if the provider is not in the config map
        config_name = "openai" if provider_name not in cls.provider_to_config_class else provider_name
        config_class_type = cls.provider_to_config_class.get(config_name)
        if class_type:
            embedder_class = load_class(class_type)
            embedder_config_class = load_class(config_class_type)
            return embedder_class(config=embedder_config_class(**config_data))
        else:
            raise ValueError(f"Unsupported Embedder provider: {provider_name}")


class VectorDBFactory:
    provider_to_class = {
        "chroma": "vectordb.chroma.ChromaDB",
        "elasticsearch": "vectordb.elasticsearch.ElasticsearchDB",
        # "opensearch": "vectordb.opensearch.OpenSearchDB",
        "opensearch": "knowledge_base.embedchain.vectordb.opensearch.OpenSearchDB",
        "pinecone": "vectordb.pinecone.PineconeDB",
        "qdrant": "vectordb.qdrant.QdrantDB",
        "weaviate": "vectordb.weaviate.WeaviateDB",
        "zilliz": "vectordb.zilliz.ZillizVectorDB",
    }
    provider_to_config_class = {
        "chroma": "config.vectordb.chroma.ChromaDbConfig",
        "elasticsearch": "config.vectordb.elasticsearch.ElasticsearchDBConfig",
        "opensearch": "knowledge_base.embedchain.config.vectordb.opensearch.OpenSearchDBConfig",
        "pinecone": "config.vectordb.pinecone.PineconeDBConfig",
        "qdrant": "config.vectordb.qdrant.QdrantDBConfig",
        "weaviate": "config.vectordb.weaviate.WeaviateDBConfig",
        "zilliz": "config.vectordb.zilliz.ZillizDBConfig",
    }

    @classmethod
    def create(cls, provider_name, config_data):
        class_type = cls.provider_to_class.get(provider_name)
        config_class_type = cls.provider_to_config_class.get(provider_name)
        if class_type:

            embedder_class = load_class(class_type)
            embedder_config_class = load_class(config_class_type)
            return embedder_class(config=embedder_config_class(**config_data))
        else:
            raise ValueError(f"Unsupported Embedder provider: {provider_name}")
