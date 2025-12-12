"""
Cargador y gestor del sistema RAG (Retrieval-Augmented Generation)
"""
import os
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

class RAGSystem:
    """
    Encapsula la lógica para inicializar y gestionar el sistema RAG.
    """
    def __init__(self, 
                 pdf_dir: str = "./data/docs", 
                 index_dir: str = "./faiss_index",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 retriever_k: int = 3):
        """
        Inicializa la configuración del sistema RAG.
        
        Args:
            pdf_dir: Directorio con los archivos PDF.
            index_dir: Directorio para guardar/cargar el índice FAISS.
            embedding_model: Nombre del modelo de embeddings.
            chunk_size: Tamaño de los fragmentos de texto.
            chunk_overlap: Superposición entre fragmentos.
            retriever_k: Número de documentos a recuperar.
        """
        self.pdf_dir = Path(pdf_dir)
        self.index_dir = Path(index_dir)
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.retriever_k = retriever_k
        
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        self.retriever = None

    def setup(self):
        """
        Ejecuta el proceso completo de inicialización del sistema RAG.
        Carga documentos, los divide, crea embeddings y el vectorstore.
        """
        if not self._docs_exist():
            print(f"Advertencia: No se encontraron PDFs en {self.pdf_dir} o el directorio no existe. El retriever no será inicializado.")
            return

        documents = self._load_pdf_documents()
        chunks = self._split_documents(documents)
        vectorstore = self._get_or_create_vectorstore(chunks)
        
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": self.retriever_k})
        print("Sistema RAG inicializado correctamente.")

    def get_retriever(self):
        """
        Devuelve el retriever si ha sido inicializado.
        
        Returns:
            El objeto retriever, o None si no se pudo inicializar.
        """
        return self.retriever
        
    def _docs_exist(self) -> bool:
        """Verifica si el directorio de PDFs existe y contiene archivos."""
        return self.pdf_dir.exists() and any(self.pdf_dir.glob("*.pdf"))

    def _load_pdf_documents(self) -> List:
        """Carga todos los documentos PDF de un directorio."""
        all_documents = []
        pdf_files = [f for f in os.listdir(self.pdf_dir) if f.endswith(".pdf")]
        
        for pdf_file in pdf_files:
            loader = PyPDFLoader(str(self.pdf_dir / pdf_file))
            docs = loader.load()
            all_documents.extend(docs)
            
        return all_documents

    def _split_documents(self, documents: List) -> List:
        """Divide documentos en fragmentos más pequeños."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        return splitter.split_documents(documents)

    def _get_or_create_vectorstore(self, chunks: List):
        """Carga un vectorstore existente o crea uno nuevo."""
        if self.index_dir.exists():
            return FAISS.load_local(
                str(self.index_dir), 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        else:
            db = FAISS.from_documents(chunks, self.embeddings)
            self.index_dir.mkdir(parents=True, exist_ok=True)
            db.save_local(str(self.index_dir))
            return db