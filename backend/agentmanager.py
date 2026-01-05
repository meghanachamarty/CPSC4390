from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
import getpass
import os
import bs4
from pathlib import Path
from langchain_community.document_loaders import WebBaseLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ENSURE user passes in the API keys to leverage the AI models
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter API key for Anthropic: ")


class AgentManager:
    def __init__(self, manager_name: str):
        self.llm = init_chat_model("anthropic:claude-sonnet-4-5")
        self.manager_name = manager_name
        self.embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
        self.vector_store = InMemoryVectorStore(self.embedding_model)


    # def ingest_doc_into_vector_db(self):
    #     # Load our documents, in this case, we have a html webpage
    #     # Only keep post title, headers, and content from the full HTML.
    #     bs4_strainer = bs4.SoupStrainer(class_=("post-title", "post-header", "post-content"))
    #     loader = WebBaseLoader(
    #         web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    #         bs_kwargs={"parse_only": bs4_strainer},
    #     )
    #     docs = loader.load()
    # 
    #     assert len(docs) == 1
    #     print(f"Total characters: {len(docs[0].page_content)}")
    # 
    #     # test print of the characters on the doc:
    #     print(docs[0].page_content[:500])
    # 
    #     # ------------------------------------------------------------------------------
    #     # Split the Documents into Chunks
    #     # ------------------------------------------------------------------------------
    # 
    #     text_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=1000,  # chunk size (characters)
    #         chunk_overlap=200,  # chunk overlap (characters)
    #         add_start_index=True,  # track index in original document
    #     )
    #     all_splits = text_splitter.split_documents(docs)
    # 
    #     print(f"Split blog post into {len(all_splits)} sub-documents.")
    # 
    #     # ------------------------------------------------------------------------------
    #     # Store the chunks into an in memory vector DB,
    #     # leverages open_ai embedding model
    #     # ------------------------------------------------------------------------------
    #     document_ids = self.vector_store.add_documents(documents=all_splits)
    #     print(document_ids[:3])

    def load_mock_course_data(self):
        """Load mock course documents from the mock_data directory."""
        mock_data_dir = Path(__file__).parent / "mock_data"
        
        if not mock_data_dir.exists():
            print("⚠️ Mock data directory not found, skipping mock data load")
            return
        
        print("🔄 Loading mock course documents...")
        all_docs = []
        
        # Load from course subdirectories (cs101, cs201, eng101, math150, etc.)
        course_dirs = [d for d in mock_data_dir.iterdir() if d.is_dir()]
        
        if not course_dirs:
            # Fallback: try loading directly from mock_data directory
            print("  ℹ️ No course subdirectories found, checking for files directly in mock_data...")
            for file_path in mock_data_dir.glob("*.txt"):
                try:
                    loader = TextLoader(str(file_path), encoding='utf-8')
                    docs = loader.load()
                    
                    # Add metadata to identify the document type
                    for doc in docs:
                        doc.metadata['source'] = file_path.name
                        doc.metadata['document_type'] = file_path.stem
                    
                    all_docs.extend(docs)
                    print(f"  ✅ Loaded {file_path.name}")
                except Exception as e:
                    print(f"  ⚠️ Error loading {file_path.name}: {e}")
        else:
            # Load from each course subdirectory
            for course_dir in course_dirs:
                course_name = course_dir.name.upper()  # cs101 -> CS101
                print(f"  📚 Loading course: {course_name}")
                
                # Load each .txt file in the course directory
                for file_path in course_dir.glob("*.txt"):
                    try:
                        loader = TextLoader(str(file_path), encoding='utf-8')
                        docs = loader.load()
                        
                        # Add metadata to identify the course, document type, and source
                        for doc in docs:
                            doc.metadata['source'] = file_path.name
                            doc.metadata['document_type'] = file_path.stem  # syllabus, assignments, etc.
                            doc.metadata['course'] = course_name  # CS101, CS201, ENG101, MATH150
                            doc.metadata['course_id'] = course_dir.name.lower()  # cs101, cs201, etc.
                        
                        all_docs.extend(docs)
                        print(f"    ✅ Loaded {course_name}/{file_path.name}")
                    except Exception as e:
                        print(f"    ⚠️ Error loading {course_name}/{file_path.name}: {e}")
        
        if not all_docs:
            print("⚠️ No mock documents found to load")
            return
        
        # Split documents into smaller, more focused chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks = more focused content
            chunk_overlap=100,  # Reduced overlap
            add_start_index=True,
        )
        all_splits = text_splitter.split_documents(all_docs)
        
        print(f"Split {len(all_docs)} documents into {len(all_splits)} chunks")
        
        # Store in vector database
        try:
            document_ids = self.vector_store.add_documents(documents=all_splits)
            print(f"✅ Successfully loaded mock course data: {len(document_ids)} chunks stored")
        except Exception as e:
            print(f"⚠️ Error storing documents (likely OpenAI quota issue): {e}")
            print("⚠️ Vector store will be empty. Some features may not work.")
