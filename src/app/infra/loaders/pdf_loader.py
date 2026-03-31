from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_pdf_documents(pdf_path: str) -> list[Document]:
    """加载 PDF 文档并返回 LangChain Document 列表。"""
    loader = PyPDFLoader(pdf_path)
    return loader.load()
