import os
import re
import logging
from typing import Optional, List, Dict, Any
from html.parser import HTMLParser
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
from sqlmodel import Session
from ..core.db import engine
from ..core.models import KnowledgeChunk

logger = logging.getLogger("phronel")

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.in_ignored_tag = False
        self.ignored_tags = {"script", "style", "head", "title", "meta", "link"}

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags:
            self.in_ignored_tag = True

    def handle_endtag(self, tag):
        if tag in self.ignored_tags:
            self.in_ignored_tag = False

    def handle_data(self, data):
        if not self.in_ignored_tag and data.strip():
            self.result.append(data.strip())

    def feed(self, data):
        self.result = []
        self.in_ignored_tag = False
        super().feed(data)

    def get_text(self) -> str:
        text = " ".join(self.result)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n\n", text)
        return text.strip()

class KnowledgeBase:
    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "、", " ", ""]
        )

    def _init_chroma(self):
        if self._client is None:
            directory = self.persist_directory
            if directory is None:
                directory = os.getenv("PHRONEL_CHROMA_DIR", "./chroma_db")
            self._client = chromadb.PersistentClient(path=directory)
            self._collection = self._client.get_or_create_collection(name="phronel_knowledge")

    @property
    def client(self):
        self._init_chroma()
        return self._client

    @property
    def collection(self):
        self._init_chroma()
        return self._collection

    def add_document(self, content: str, source: str):
        """Adds a document to the knowledge base."""
        # 1. Split text into chunks
        chunks = self.text_splitter.split_text(content)
        
        if not chunks:
            return 0

        # 2. Add to ChromaDB
        # Generate IDs based on timestamp and index
        timestamp = datetime.now().timestamp()
        ids = [f"{source}_{timestamp}_{i}" for i in range(len(chunks))]
        # ChromaDB expects metadatas to be a list of dicts, same length as documents
        metadatas = [{"source": source} for _ in chunks]

        self.collection.add( # type: ignore
            documents=chunks,
            metadatas=metadatas, # type: ignore
            ids=ids
        )

        # 3. Add to SQLite (KnowledgeChunk table) for reference
        # Use a new session for this operation
        with Session(engine) as session:
            for i, chunk_text in enumerate(chunks):
                k_chunk = KnowledgeChunk(
                    content=chunk_text,
                    source=source,
                    embedding_id=ids[i]
                )
                session.add(k_chunk)
            session.commit()
            
        return len(chunks)

    def query(self, query_text: str, n_results: int = 3, where: Optional[dict] = None):
        """Queries the knowledge base for relevant chunks."""
        results = self.collection.query( # type: ignore
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        # Flatten results
        if results['documents']:
            return [doc for doc in results['documents'][0]]
        return []

    def list_sources(self) -> List[Dict[str, Any]]:
        """Lists all imported knowledge sources, chunk counts, and import dates."""
        from sqlmodel import select, func
        sources_list = []
        try:
            with Session(engine) as session:
                # Query unique sources and count chunks
                stmt = select(
                    KnowledgeChunk.source,
                    func.count(KnowledgeChunk.id).label("chunk_count"), # type: ignore
                    func.min(KnowledgeChunk.created_at).label("imported_at")
                ).group_by(KnowledgeChunk.source)
                results = session.exec(stmt).all()
                
                for source, chunk_count, imported_at in results:
                    sources_list.append({
                        "source": source,
                        "chunk_count": chunk_count,
                        "imported_at": imported_at
                    })
        except Exception as e:
            logger.error(f"[KnowledgeBase] Failed to list sources from SQLite: {e}")
        return sources_list

    def get_chunks_by_source(self, source_name: str) -> List[KnowledgeChunk]:
        """Gets all text chunks belonging to a specific source."""
        from sqlmodel import select
        try:
            with Session(engine) as session:
                stmt = select(KnowledgeChunk).where(KnowledgeChunk.source == source_name)
                return session.exec(stmt).all() # type: ignore
        except Exception as e:
            logger.error(f"[KnowledgeBase] Failed to get chunks for source '{source_name}': {e}")
        return []

    def delete_source(self, source_name: str) -> int:
        """Deletes all chunks of a source from both SQLite and ChromaDB."""
        from sqlmodel import select, delete, func
        deleted_count = 0
        try:
            # 1. Delete from ChromaDB
            self.collection.delete(where={"source": source_name}) # type: ignore
            logger.info(f"[KnowledgeBase] Deleted source '{source_name}' from ChromaDB.")
            
            # 2. Delete from SQLite
            with Session(engine) as session:
                # Get the count first for reporting
                stmt_count = select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.source == source_name) # type: ignore
                deleted_count = session.exec(stmt_count).one()
                
                # Delete rows
                stmt_del = delete(KnowledgeChunk).where(KnowledgeChunk.source == source_name) # type: ignore
                session.exec(stmt_del)
                session.commit()
                logger.info(f"[KnowledgeBase] Deleted {deleted_count} chunks of source '{source_name}' from SQLite.")
                
        except Exception as e:
            logger.error(f"[KnowledgeBase] Failed to delete source '{source_name}': {e}")
        return deleted_count

    def add_url(self, url: str) -> int:
        """Ingests a Web URL, parses HTML, and adds plain text to the knowledge base."""
        import urllib.request
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode("utf-8", errors="ignore")
                
            parser = HTMLTextExtractor()
            parser.feed(html_content)
            plain_text = parser.get_text()
            
            if not plain_text:
                logger.warning(f"[KnowledgeBase] No plain text extracted from URL: {url}")
                return 0
                
            logger.info(f"[KnowledgeBase] Extracted {len(plain_text)} characters from URL '{url}'. Ingesting...")
            return self.add_document(content=plain_text, source=url)
        except Exception as e:
            logger.error(f"[KnowledgeBase] Failed to ingest URL '{url}': {e}")
            raise e

# Global instance
knowledge_base = KnowledgeBase()
