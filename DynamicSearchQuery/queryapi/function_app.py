import os
import json
import logging
import requests
import azure.functions as func

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from instructions import INSTRUCTIONS

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

def parse_input(req: func.HttpRequest):
    """Extracts message, agentid, threadid from request."""
    message = req.params.get('message')
    agentid = req.params.get('agentid')
    threadid = req.params.get('threadid')
    
    if not message or not agentid:
        try:
            req_body = req.get_json()
        except ValueError:
            req_body = None

        if req_body:
            message = req_body.get('message')
            agentid = req_body.get('agentid')
            threadid = req_body.get('threadid')

    return message, agentid, threadid

def get_project_client():
    """Creates an AIProjectClient with DefaultAzureCredential."""
    conn_str = os.environ.get("AIProjectConnString", "")
    if not conn_str:
        raise ValueError("Missing AIProjectConnString")
    return AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str
    )

def ensure_agent_and_thread(project_client, agentid, threadid):
    """Retrieves or creates agent/thread, returns agent object and thread object."""
    agent = project_client.agents.get_agent(agentid)
    if not agent:
        raise ValueError(f"Agent with ID {agentid} not found.")

    thread = project_client.agents.get_thread(threadid) if threadid else None
    if not thread:
        thread = project_client.agents.create_thread()

    return agent, thread

def create_and_run_agent(project_client, agent, thread, message, instructions):
    """
    Sends user message and instructions to the agent, processes the run, 
    then returns the assistant message (JSON query).
    """
    project_client.agents.create_message(thread_id=thread.id, role="user", content=message)
    project_client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent.id,
        instructions=instructions,
        temperature=0,
        top_p=1
    )

    messages = project_client.agents.list_messages(thread_id=thread.id)
    if not messages or not messages.data:
        raise ValueError("No messages found in the thread.")

    assistant_messages = [m for m in messages.data if m["role"] == "assistant"]
    if not assistant_messages:
        return "No assistant message found."

    # Get the last assistant message
    assistant_message = assistant_messages[-1]
    return " ".join(
        part["text"]["value"] for part in assistant_message["content"] if "text" in part
    )

def validate_json_query(assistant_text):
    """Ensures the assistant text is a valid JSON string."""
    if assistant_text == "No assistant message found.":
        raise ValueError("No valid assistant message was generated.")
    try:
        json.loads(assistant_text)
    except json.JSONDecodeError:
        raise ValueError("Assistant message was not valid JSON.")
    return assistant_text

def call_azure_search(assistant_text):
    """Posts the JSON query (assistant_text) to Azure Search and returns the HTTP response."""
    search_endpoint = os.environ.get("SEARCH_ENDPOINT", "<YourSearchEndpoint>")
    search_index = os.environ.get("SEARCH_INDEX", "<YourSearchIndex>")
    api_key = os.environ.get("SEARCH_API_KEY", "<YourSearchApiKey>")
    if not api_key:
        raise ValueError("Missing SEARCH_API_KEY.")

    search_url = f"{search_endpoint}/indexes/{search_index}/docs/search?api-version=2024-07-01"
    headers = { "Content-Type": "application/json", "api-key": api_key }
    response = requests.post(search_url, headers=headers, data=assistant_text)
    return response

@app.route(route="agent_httptrigger")
def agent_httptrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")
    try:
        message, agentid, threadid = parse_input(req)
        if not message or not agentid:
            return func.HttpResponse(
                "Pass in a message and agentid in the query string or request body.",
                status_code=400
            )

        project_client = get_project_client()
        agent, thread = ensure_agent_and_thread(project_client, agentid, threadid)

        
        assistant_text = create_and_run_agent(project_client, agent, thread, message, INSTRUCTIONS)
        logging.info(f"Generated Azure AI Search Query: {assistant_text}")
        
        assistant_text = validate_json_query(assistant_text)
        response = call_azure_search(assistant_text)

        return func.HttpResponse(
            response.text,
            status_code=response.status_code,
            mimetype="application/json"
        )
    except ValueError as ve:
        logging.error(str(ve))
        if "missing" in str(ve).lower():
            return func.HttpResponse(
                f"Internal Server Error: {ve}",
                status_code=500
            )
        return func.HttpResponse(
            str(ve),
            status_code=400
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return func.HttpResponse(
            "Internal Server Error: " + str(e),
            status_code=500
        )