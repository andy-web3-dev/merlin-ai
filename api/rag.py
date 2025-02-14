import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_chroma import Chroma
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate


llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
resp = llm.invoke([HumanMessage("Hi there?")])

doc_path = "./data/movement-whitepaper_en.txt"
text = open(doc_path, "r").read()

splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
chunks = splitter.split_text(text)

vector_store = InMemoryVectorStore(embedding=embeddings)
vector_store.add_texts(chunks)

vector_store_chroma = Chroma(embedding_function=embeddings)
vector_store_chroma.add_texts(chunks)

questions = ["What is the movement?", "What is the purpose of the movement?", "What is the goal of the movement?"]

# for q in questions:
q = questions[0]
q_vec = embeddings.embed_query(q)
results = vector_store.similarity_search_by_vector(q_vec, k=3)
print(f"Question: {q}")
for r in results:
    print(f"Text: {r.page_content}\n")

context = "\n".join([r.page_content for r in results])
prompt = hub.pull("rlm/rag-prompt")

example_messages = prompt.invoke(
    {"context": context, "question": q}
).to_messages()

assert len(example_messages) == 1
print(example_messages[0].content)

resp = llm.invoke(example_messages)
print(resp.content)


template = ChatPromptTemplate([
    ("system", "You are a helpful AI bot. Your name is {name}."),
    ("human", "Hello, how are you doing?"),
    ("ai", "I'm doing well, thanks!"),
    ("human", "{user_input}"),
])

prompt_value = template.invoke(
    {
        "name": "Bob",
        "user_input": "What is your name?"
    }
)

from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
  ("human", "You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.\nQuestion: {question}\nContext: {context} \nAnswer:"),
])

import chromadb
client = chromadb.Client()
from chromadb.utils import embedding_functions
ef = embedding_functions.create_langchain_embedding()
ef.embed_query("What is the movement?")



