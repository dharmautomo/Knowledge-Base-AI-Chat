from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TextProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.vector_store = None

    def process_document(self, text):
        """
        Process a document by splitting it into chunks and creating vector embeddings.
        """
        try:
            logger.debug(f"Processing document of length: {len(text)}")

            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            logger.debug(f"Document split into {len(chunks)} chunks")

            # Create vector store
            self.vector_store = FAISS.from_texts(chunks, self.embeddings)
            logger.debug("Vector store created successfully")

            return len(chunks)

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def get_relevant_context(self, query, k=3):
        """
        Retrieve the most relevant context for a given query.
        """
        if not self.vector_store:
            logger.warning("No vector store available. Process a document first.")
            return ""

        try:
            # Search for relevant chunks
            relevant_chunks = self.vector_store.similarity_search(query, k=k)
            context = "\n".join(doc.page_content for doc in relevant_chunks)

            logger.debug(f"Retrieved {len(relevant_chunks)} relevant chunks for query")
            return context

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise