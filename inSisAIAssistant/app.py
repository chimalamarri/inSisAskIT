from flask import Flask, request
from flask_cors import CORS
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain.schema import Document
import requests
import json
import config
from datetime import datetime
import threading
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app)

# Logging configuration
log_file = "inSisAiAssistant.log"  # Log file path
handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=3)  # Max 100 KB, keep 3 backups
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

# Add the handler to the Flask app's logger
app.logger.addHandler(handler)

# Persistent folder for vector storage
folder_path = "db"

# Embedding function
embedding = FastEmbedEmbeddings()

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False
)

# In-memory conversation history
conversation_history = {}
def flatten_json(data, fields_to_keep, parent_key='', separator='.'):
    """
    Recursively flatten a nested JSON object, keeping only specified fields.
    """
    items = []
    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_json(value, fields_to_keep, new_key, separator=separator).items())
        elif isinstance(value, list):
            # Process each element in the list
            for i, item in enumerate(value):
                list_key = f"{new_key}[{i}]"
                if isinstance(item, dict):
                    items.extend(flatten_json(item, fields_to_keep, list_key, separator=separator).items())
                elif list_key in fields_to_keep:
                    items.append((list_key, item))
        else:
            if key in fields_to_keep or new_key in fields_to_keep:
                items.append((new_key, value))
    return dict(items)


def save_conversation(user_id, query, response):
    """
    Save the conversation to memory for a specific user.
    """
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"query": query, "response": response})

def get_conversation_history(user_id):
    """
    Retrieve the conversation history for a specific user.
    """
    return conversation_history.get(user_id, [])

@app.route("/Ask/Update", methods=["POST"])
def upload_json():
    """
    Fetch JSON from multiple APIs with different data structures, process them, and store the results.
    """
    app.logger.info("Vector DB is Updating")

    apis = [
        {
            "url": f"{config.InSisServerURL}/inSis/api/InfoviewApp/TagSummaryDetailsInfoByProperties?pageNo=1&pageSize=100000&cmpid=1&api_key=api",
            "fields_to_keep": {
                "ValuePath", "GroupNames", "Description"
            },
            "headers": None,
            "is_list": True,
            "rename_field": {"ValuePath": "Tag Name"},
        },
        {
            "url": f"{config.InSisServerURL}/inSis/api/InfoviewApp/GetInfoViewRecentList?myListType=3&username=admin&uname=admin",
            "fields_to_keep": {
                "Name"
            },
            "headers": {
                "insis_token": config.insistoken,
                "insis_key": config.insiskey
            },
            "is_list": False,
            "rename_field": {"Name": "Infoview Name"},
        },
        {
            "url": f"{config.InSisServerURL}/inSis/home/GetAllDashBoardList_App?myListType=5&uname=admin",
            "fields_to_keep": {
                "Name"
            },
            
            "is_list": False,
            "rename_field": {"Name": "Dashboard Name"},
        },
        {
            "url": f"{config.InSisServerURL}/inSis/api/InfoviewApp/GetAllSmartTrendViews",
            "fields_to_keep": {
                "Text"
            },
            
            "is_list": False,
            "rename_field": {"Name": "Smart Trend Name"},
        }
    ]

    combined_json_data = []

    for api in apis:
        try:
            response = requests.get(api["url"], headers=api.get("headers"))
            response.raise_for_status()
            json_data = response.json()

            if api["is_list"]:
                json_data = json_data.get("Data", [])
            if isinstance(json_data, list):
                flattened_data = [flatten_json(item, api["fields_to_keep"]) for item in json_data]
            else:
                flattened_data = [flatten_json(json_data, api["fields_to_keep"])]

            if api.get("rename_field"):
                for item in flattened_data:
                    for old_field, new_field in api["rename_field"].items():
                        if old_field in item:
                            item[new_field] = item.pop(old_field)

            combined_json_data.extend(flattened_data)
        except requests.exceptions.RequestException as e:
            return {"status": "Error", "message": f"API request failed for {api['url']}: {e}"}, 500
        except Exception as e:
            return {"status": "Error", "message": f"Error processing data from {api['url']}: {e}"}, 500

    if not combined_json_data:
        return {"status": "Error", "message": "No JSON data retrieved from the APIs"}, 400

    try:
        # Convert combined data into documents
        documents = [Document(page_content=json.dumps(entry)) for entry in combined_json_data]

        chunks = []
        for doc in documents:
            chunks.extend(text_splitter.split_documents([doc]))

        # Process data into the vector store
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=folder_path
        )
        vector_store.persist()
        app.logger.info("Vector DB Updated Successfully")

        return {"status": "Success", "message": "JSON data uploaded and processed successfully from multiple APIs"}
    except Exception as e:
        app.logger.info("Vector DB Updation Failed!")
        return {"status": "Error", "message": f"Failed to process JSON data: {e}"}, 500



@app.route("/Ask/Ask", methods=["POST"])
@app.route("/Ask/ask_json", methods=["POST"])
def ask_json():
    """
    Process a query and return the response.
    """
    app.logger.info("Query is Sent to the Route")
    user_id = request.json.get("user_id")  # Expect user_id in the request
    query = request.json.get("query")
    if not query or not user_id:
        return {"status": "Error", "message": "Query or user_id is missing"}, 400

    # Retrieve conversation history
    history = get_conversation_history(user_id)
    chat_context = "\n\n".join([f"User_Query: {c['query']}\nAI_Response: {c['response']}" for c in history])

    # ChatGPT-like API URL
    chatgpt_api_url = config.rewrite_query_for_AI_Assistant

    # Step 1: Send the query with context to ChatGPT-like API
    try:
        initial_payload = {"question": query, "history": chat_context}
        response = requests.post(chatgpt_api_url, json=initial_payload, timeout=30)
        response.raise_for_status()
        chatgpt_response = response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "Error", "message": f"ChatGPT API call failed: {e}"}, 500

    # Extract fields from the response
    send_to_rag = chatgpt_response.get("send_to_rag", "").lower() == "yes"
    rebuilt_query = chatgpt_response.get("rebuilt_query", "")
    stopwords_removed_query = chatgpt_response.get("stopwords_removed_query", "")
    answer = chatgpt_response.get("answer", "")

    
    if True:
        # Step 2: Use RAG to retrieve relevant context
        try:
            vector_store = Chroma(persist_directory=folder_path, embedding_function=embedding)
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 20})
            relevant_docs = retriever.get_relevant_documents(stopwords_removed_query)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
        except Exception as e:
            return {"status": "Error", "message": f"RAG retrieval failed: {e}"}, 500
    

    # Step 3: Send query and context to the additional API to extract function name
    extraction_api_url = config.function_calling_for_AI_Assistant
    try:
        # Get current date and time
        current_datetime = datetime.now()

        # Format the date and time
        formatted_datetime = "Current Date and Time is" + str(current_datetime.strftime("%Y-%m-%dT%H:%M:%S"))

        dynamic_query = f"original_query: {query} + rebuilt_query: {rebuilt_query}"
        extraction_payload = {"query": dynamic_query, "context": context,"datetime":formatted_datetime}
        extraction_response = requests.post(extraction_api_url, json=extraction_payload, timeout=30)
        extraction_response.raise_for_status()
        extraction_result = extraction_response.json()
        
        function_name = extraction_result.get("function_name", "")
        if function_name.startswith("tag_value"):
            tag_name = extraction_result.get("parameters")
            if "value" in tag_name.lower():
                tag_name = tag_name.lower()[:-6]
            tag_api_url = f"{config.InSisServerURL}/inSis/api/InfoviewApp/GetTagsForApp?SearchStr={tag_name}&uname=admin"
            HEADERS = {
                "insis_token": config.insistoken,
                "insis_key": config.insiskey,
            }

            # Call the tag API to update the context
            tag_response = requests.get(tag_api_url, headers=HEADERS,timeout=30)
            tag_response.raise_for_status()
            tag_data = tag_response.json()
            context = f"\n\nTag Data: {json.dumps(tag_data)} + function_name = tag_value"
            
    except requests.exceptions.RequestException as e:
        return {"status": "Error", "message": f"Function extraction or tag API call failed: {e}"}, 500

    
    # Step 4: Send rebuilt query and updated context to Copilot Studio API
    copilot_api_url = config.chatGPT_for_AI_Assistant
    copilot_payload = {"query": dynamic_query, "context": context}

    try:
        copilot_response = requests.post(copilot_api_url, json=copilot_payload, timeout=30)
        copilot_response.raise_for_status()
        copilot_result = copilot_response.json()
        answer = copilot_result.get("responsev2", {}).get("predictionOutput", {}).get("text", answer)

        # Save the conversation
        save_conversation(user_id, query, answer)
        app.logger.info("Response is Sent back to the application")
        return {
            "query": query,
            "rebuilt_query": rebuilt_query,
            "context_used": context,
            "answer": answer,
            "function_name":extraction_result.get("function_name", ""),
            "parameters":extraction_result.get("parameters", ""),
            "start_time":extraction_result.get("start_time", ""),
            "end_time":extraction_result.get("end_time",""),
            "trend_type":extraction_result.get("trend_type", ""),
            "interval":extraction_result.get("interval", "")
        }
    except requests.exceptions.RequestException as e:
        return {"status": "Error", "message": f"Copilot API call failed: {e}"}, 500

#periodically update the RAG
@app.route('/Ask/UpdateRAG', methods=['GET'])
def trigger_task():
    thread = threading.Thread(target=upload_json)
    thread.start()
    return ({"message": "Task started!"}), 200

@app.route("/Ask")
def home():
    return {"status": "Server running", "message": "Welcome to the AI Assistant!"}

if __name__ == "__main__":
    app.run()
