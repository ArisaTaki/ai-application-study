import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.contracts.embeddings import EmbeddingModel
from app.infra.factories.embedding_factory import build_embeddings
from app.infra.loaders.pdf_loader import load_pdf_documents

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self, persist_directory: str = "./chroma_db/psychology_kb"):
        self.persist_directory = persist_directory
        self.embedding_model: EmbeddingModel = build_embeddings(use_case="rag")
        self.vector_store = None

        # 配置文档分块器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, # 每个块的最大字符数
            chunk_overlap=50, # 块之间的重叠字符数
            length_function=len, # 计算文本长度的函数
            separators=["\n\n", "\n", " ", "。", "，", "！", "？", "；", "：", ".", "","?"] # 分块时优先使用的分隔符    
        )

    def load_pdf_documents(self, pdf_path: str) -> list[Document]:
        """加载PDF文档"""
        documents = load_pdf_documents(pdf_path)
        logger.info(f"成功加载PDF文档: {pdf_path}，共 {len(documents)} 页")
        return documents
    
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """将文档分块"""
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"成功将文档分块，共 {len(split_docs)} 块")
        return split_docs
