from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph import END
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import json
import os
import yaml

config = yaml.safe_load(open("config/graph.yaml", "r"))
if config['vector_database']['embedding'] == 'OpenAI':
    embedding_model_name = config['vector_database']['embedding_model']
    embeddings = OpenAIEmbeddings(model=embedding_model_name)
    db_dir = os.path.join("./db", embedding_model_name)
    print("Using embedding at: ", db_dir)
    chroma = Chroma(persist_directory=db_dir, embedding_function=embeddings)
else:
    embedding_model_name = None
    embeddings = None
    chroma = None
llm = ChatOpenAI(model=config['chat_model']['model'])
# by default: openai API key is in the environment variable OPENAI_API_KEY
coins_list = json.load(open(config['tool_utils']['coin_list_path'], 'r'))


@tool(response_format="content_and_artifact")
def retrieve(query: str, k=5):
    """Retrieve information related to a query."""
    # print("AI agent retrieving relevant information...")
    retrieved_docs = chroma.similarity_search(query, k=k)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

def get_token_price(name):
    """
    Fetch the current USD price of a cryptocurrency token using CoinGecko's API.
    """
    coins_list = json.load(open('data/coins_list.json', 'r'))
    lower_name = name.lower()
    matched_coins = []
    for coin in coins_list:
        if coin.get("name", "").lower() == lower_name:
            matched_coins.append(coin)
    if not matched_coins:
        for coin in coins_list:
            if coin.get("symbol", "").lower() == lower_name:
                matched_coins.append(coin)
    if len(matched_coins) == 0:
        print(f"Token '{name}' not found on CoinGecko.")
        return None

    coin_ids = ",".join([coin["id"] for coin in matched_coins])
    price_url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_ids,
        "vs_currencies": "usd",
        "include_market_cap": "true",
    }
    try:
        price_response = requests.get(price_url, params=params)
        price_response.raise_for_status()
        price_data = price_response.json()
        prices = {}
        for id, price in price_data.items():
            if price and price.get("usd_market_cap") and price.get("usd"):
                prices[id] = price
        highest_market_cap = max(prices.items(), key=lambda item: item[1]['usd_market_cap'])
        return highest_market_cap[1]["usd"]

    except requests.RequestException as e:
        print(f"Error fetching price data: {e}")
        return None

@tool(response_format="content")
def token_price(query: str) -> str:
    """
    Get the current price of a token from CoinGecko.
    The 'query' should be the token name or token symbol.
    """
    symbol = query.strip()
    price = get_token_price(symbol)
    if price is None:
        return f"Sorry, I couldn't find a price for '{symbol}'."
    else:
        return f"The current price of {symbol.upper()} is ${price:.4f} (USD)."

def query_or_respond(state: MessagesState):
    """Generate tool call for retrieval or respond."""
    llm_with_tools = llm.bind_tools([
        retrieve,
        token_price
    ])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def generate(state: MessagesState):
    """Generate answer using context from tool messages."""
    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]
    docs_content = "\n\n".join(doc.content for doc in tool_messages)
    system_message_content = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know. "
        "Use three sentences maximum and keep the answer concise."
        "\n\n" + docs_content
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system")
           or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages
    response = llm.invoke(prompt)
    return {"messages": [response]}

def create_graph():
    tools = ToolNode([
        retrieve,
        token_price
    ])
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(tools)
    graph_builder.add_node(generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)

    graph = graph_builder.compile()
    return graph

def chatbot(graph):
    """
    Continually prompt the user for input, run the graph, and stream the AI's response.
    Ends when the user types 'bye', 'quit', or 'exit'.
    """
    # Initialize conversation state with a system message.
    state = {"messages": [
        {
            "role": "system",
            "content": (
                "You are a knowledgeable assistant about the Movement network "
                "and its ecosystem. You can retrieve context from a vector store "
                "whenever needed. Answer truthfully; if unsure, say so. Don't "
                "answer questions that's not about blockchain."
            )
        }
    ]}

    while True:
        user_input = input("\nUser: ").strip()
        if user_input.lower() in ["bye", "quit", "exit"]:
            print("AI: Bye! Have a nice day!")
            break

        state["messages"].append(HumanMessage(user_input))
        print("Merlin: ", end="", flush=True)

        # Stream the response from the graph.
        for (stream_mode, data) in graph.stream(state, stream_mode=["messages", "values"]):
            if stream_mode == "messages":
                if isinstance(data[0], AIMessage):
                    print(data[0].content, end="", flush=True)
            else:
                state = data

        print()  # Newline after finishing the streamed response.

if __name__ == "__main__":
    graph = create_graph()
    chatbot(graph)
