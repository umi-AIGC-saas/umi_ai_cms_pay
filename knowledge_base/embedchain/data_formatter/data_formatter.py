from importlib import import_module
from typing import Optional

from knowledge_base.embedchain.chunkers.base_chunker import BaseChunker
from knowledge_base.embedchain.config import AddConfig
from knowledge_base.embedchain.config.add_config import ChunkerConfig, LoaderConfig
from knowledge_base.embedchain.helpers.json_serializable import JSONSerializable
from knowledge_base.embedchain.loaders.base_loader import BaseLoader
from knowledge_base.embedchain.models.data_type import DataType


class DataFormatter(JSONSerializable):
    """
    DataFormatter is an internal utility class which abstracts the mapping for
    loaders and chunkers to the data_type entered by the user in their
    .add or .add_local method call
    """

    def __init__(
        self,
        data_type: DataType,
        config: AddConfig,
        loader: Optional[BaseLoader] = None,
        chunker: Optional[BaseChunker] = None,
    ):
        """
        Initialize a dataformatter, set data type and chunker based on datatype.

        :param data_type: The type of the data to load and chunk.
        :type data_type: DataType
        :param config: AddConfig instance with nested loader and chunker config attributes.
        :type config: AddConfig
        """
        self.loader = self._get_loader(data_type=data_type, config=config.loader, loader=loader)
        self.chunker = self._get_chunker(data_type=data_type, config=config.chunker, chunker=chunker)

    def _lazy_load(self, module_path: str):
        module_path, class_name = module_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)

    def _get_loader(self, data_type: DataType, config: LoaderConfig, loader: Optional[BaseLoader]) -> BaseLoader:
        """
        Returns the appropriate data loader for the given data type.

        :param data_type: The type of the data to load.
        :type data_type: DataType
        :param config: Config to initialize the loader with.
        :type config: LoaderConfig
        :raises ValueError: If an unsupported data type is provided.
        :return: The loader for the given data type.
        :rtype: BaseLoader
        """
        loaders = {
            DataType.YOUTUBE_VIDEO: "knowledge_base.embedchain.loaders.youtube_video.YoutubeVideoLoader",
            DataType.PDF_FILE: "knowledge_base.embedchain.loaders.pdf_file.PdfFileLoader",
            DataType.WEB_PAGE: "knowledge_base.embedchain.loaders.web_page.WebPageLoader",
            DataType.QNA_PAIR: "knowledge_base.embedchain.loaders.local_qna_pair.LocalQnaPairLoader",
            DataType.TEXT: "knowledge_base.embedchain.loaders.local_text.LocalTextLoader",
            DataType.DOCX: "knowledge_base.embedchain.loaders.docx_file.DocxFileLoader",
            DataType.SITEMAP: "knowledge_base.embedchain.loaders.sitemap.SitemapLoader",
            DataType.XML: "knowledge_base.embedchain.loaders.xml.XmlLoader",
            DataType.DOCS_SITE: "knowledge_base.embedchain.loaders.docs_site_loader.DocsSiteLoader",
            DataType.CSV: "knowledge_base.embedchain.loaders.csv.CsvLoader",
            DataType.MDX: "knowledge_base.embedchain.loaders.mdx.MdxLoader",
            DataType.IMAGES: "knowledge_base.embedchain.loaders.images.ImagesLoader",
            DataType.UNSTRUCTURED: "knowledge_base.embedchain.loaders.unstructured_file.UnstructuredLoader",
            DataType.JSON: "knowledge_base.embedchain.loaders.json.JSONLoader",
            DataType.OPENAPI: "knowledge_base.embedchain.loaders.openapi.OpenAPILoader",
            DataType.GMAIL: "knowledge_base.embedchain.loaders.gmail.GmailLoader",
            DataType.NOTION: "knowledge_base.embedchain.loaders.notion.NotionLoader",
            DataType.SUBSTACK: "knowledge_base.embedchain.loaders.substack.SubstackLoader",
            DataType.YOUTUBE_CHANNEL: "knowledge_base.embedchain.loaders.youtube_channel.YoutubeChannelLoader",
            DataType.DISCORD: "knowledge_base.embedchain.loaders.discord.DiscordLoader",
            DataType.RSSFEED: "knowledge_base.embedchain.loaders.rss_feed.RSSFeedLoader",
            DataType.BEEHIIV: "knowledge_base.embedchain.loaders.beehiiv.BeehiivLoader",
            DataType.DIRECTORY: "knowledge_base.embedchain.loaders.directory_loader.DirectoryLoader",
            DataType.SLACK: "knowledge_base.embedchain.loaders.slack.SlackLoader",
        }

        if data_type == DataType.CUSTOM or loader is not None:
            loader_class: type = loader
            if loader_class:
                return loader_class
        elif data_type in loaders:
            loader_class: type = self._lazy_load(loaders[data_type])
            return loader_class()

        raise ValueError(
            f"Cant find the loader for {data_type}.\
                    We recommend to pass the loader to use data_type: {data_type},\
                        check `https://docs.ai/data-sources/overview`."
        )

    def _get_chunker(self, data_type: DataType, config: ChunkerConfig, chunker: Optional[BaseChunker]) -> BaseChunker:
        """Returns the appropriate chunker for the given data type (updated for lazy loading)."""
        chunker_classes = {
            DataType.YOUTUBE_VIDEO: "knowledge_base.embedchain.chunkers.youtube_video.YoutubeVideoChunker",
            DataType.PDF_FILE: "knowledge_base.embedchain.chunkers.pdf_file.PdfFileChunker",
            DataType.WEB_PAGE: "knowledge_base.embedchain.chunkers.web_page.WebPageChunker",
            DataType.QNA_PAIR: "knowledge_base.embedchain.chunkers.qna_pair.QnaPairChunker",
            DataType.TEXT: "knowledge_base.embedchain.chunkers.text.TextChunker",
            DataType.DOCX: "knowledge_base.embedchain.chunkers.docx_file.DocxFileChunker",
            DataType.SITEMAP: "knowledge_base.embedchain.chunkers.sitemap.SitemapChunker",
            DataType.XML: "knowledge_base.embedchain.chunkers.xml.XmlChunker",
            DataType.DOCS_SITE: "knowledge_base.embedchain.chunkers.docs_site.DocsSiteChunker",
            DataType.CSV: "knowledge_base.embedchain.chunkers.table.TableChunker",
            DataType.MDX: "knowledge_base.embedchain.chunkers.mdx.MdxChunker",
            DataType.IMAGES: "knowledge_base.embedchain.chunkers.images.ImagesChunker",
            DataType.UNSTRUCTURED: "knowledge_base.embedchain.chunkers.unstructured_file.UnstructuredFileChunker",
            DataType.JSON: "knowledge_base.embedchain.chunkers.json.JSONChunker",
            DataType.OPENAPI: "knowledge_base.embedchain.chunkers.openapi.OpenAPIChunker",
            DataType.GMAIL: "knowledge_base.embedchain.chunkers.gmail.GmailChunker",
            DataType.NOTION: "knowledge_base.embedchain.chunkers.notion.NotionChunker",
            DataType.SUBSTACK: "knowledge_base.embedchain.chunkers.substack.SubstackChunker",
            DataType.YOUTUBE_CHANNEL: "knowledge_base.embedchain.chunkers.common_chunker.CommonChunker",
            DataType.DISCORD: "knowledge_base.embedchain.chunkers.common_chunker.CommonChunker",
            DataType.CUSTOM: "knowledge_base.embedchain.chunkers.common_chunker.CommonChunker",
            DataType.RSSFEED: "knowledge_base.embedchain.chunkers.rss_feed.RSSFeedChunker",
            DataType.BEEHIIV: "knowledge_base.embedchain.chunkers.beehiiv.BeehiivChunker",
            DataType.DIRECTORY: "knowledge_base.embedchain.chunkers.common_chunker.CommonChunker",
            DataType.SLACK: "knowledge_base.embedchain.chunkers.common_chunker.CommonChunker",
        }

        if chunker is not None:
            return chunker
        elif data_type in chunker_classes:
            chunker_class = self._lazy_load(chunker_classes[data_type])
            chunker = chunker_class(config)
            chunker.set_data_type(data_type)
            return chunker

        raise ValueError(
            f"Cant find the chunker for {data_type}.\
                We recommend to pass the chunker to use data_type: {data_type},\
                    check `https://docs.ai/data-sources/overview`."
        )
