from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from chromadb.utils import embedding_functions
import yaml

config = yaml.safe_load(open("config/graph.yaml", "r"))

docs_dir = config['vector_database']['docs_dir']
persist_dir = config['vector_database']['db_dir']
embedding_model_name = config['vector_database']['embedding_model']
# embedding_model_name = "chroma_default"
db_dir = os.path.join(persist_dir, embedding_model_name)

os.makedirs(db_dir, exist_ok=True)
docs_path = [f for f in os.listdir(docs_dir) if f.endswith(".txt")]
embedding = OpenAIEmbeddings(model=embedding_model_name)
default_ef = embedding_functions.DefaultEmbeddingFunction()
splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
vector_store_chroma = Chroma(
    embedding_function=embedding,
    # embedding_function=default_ef,
    persist_directory=db_dir
)
# iterate over documents
sub_dirs = [x for x in os.listdir(docs_dir) if os.path.isdir(os.path.join(docs_dir, x))]
for d in sub_dirs:
    # d = "blogs"
    sub_dir = os.path.join(docs_dir, d)
    docs_path = [f for f in os.listdir(sub_dir) if f.endswith(".txt")]
    for doc_path in docs_path:
        loader = TextLoader(
            file_path=os.path.join(sub_dir, doc_path),
            encoding="utf-8"
        )
        doc = loader.load()[0]
        chunks = splitter.split_text(doc.page_content)
        doc_ids = vector_store_chroma.add_texts(chunks)
        print(f"Added {len(doc_ids)} chunks from {doc_path}")
