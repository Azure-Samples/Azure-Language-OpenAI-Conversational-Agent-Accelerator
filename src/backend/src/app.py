import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from semantic_kernel_orchestrator import SemanticKernelOrchestrator
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AgentGroupChat
from dotenv import load_dotenv
load_dotenv()

# Environment variables
PROJECT_ENDPOINT = os.environ.get("AGENTS_PROJECT_ENDPOINT")
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")
AGENT_IDS = {
    "TRIAGE_AGENT_ID": os.environ.get("TRIAGE_AGENT_ID"),
    "HEAD_SUPPORT_AGENT_ID": os.environ.get("HEAD_SUPPORT_AGENT_ID"),
    "ORDER_STATUS_AGENT_ID": os.environ.get("ORDER_STATUS_AGENT_ID"),
    "ORDER_CANCEL_AGENT_ID": os.environ.get("ORDER_CANCEL_AGENT_ID"),
    "ORDER_REFUND_AGENT_ID": os.environ.get("ORDER_REFUND_AGENT_ID"),
}

class ChatRequest(BaseModel):
    message: str

# Set up Jinja2 environment for templates
# templates = Environment(loader=FileSystemLoader("dist"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    print("Setting up Azure credentials and client...")
    print(f"Using PROJECT_ENDPOINT: {PROJECT_ENDPOINT}")
    print(f"Using MODEL_NAME: {MODEL_NAME}")
    creds = DefaultAzureCredential()
    await creds.__aenter__()

    client = AzureAIAgent.create_client(credential=creds, endpoint=PROJECT_ENDPOINT)
    await client.__aenter__()

    orchestrator = SemanticKernelOrchestrator(client, MODEL_NAME, PROJECT_ENDPOINT, AGENT_IDS)
    await orchestrator.initialize()

    # Store in app state
    app.state.creds = creds
    app.state.client = client
    app.state.orchestrator = orchestrator

    yield

    # Teardown
    await client.__aexit__(None, None, None)
    await creds.__aexit__(None, None, None)

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
# app.mount("/static", StaticFiles(directory="dist"), name="static")

# Define the root path for the static files and templates
# @app.get("/", response_class=HTMLResponse)
# async def home_page(request: Request):
#     """
#     Render the home page using a template.
#     """
#     template = templates.get_template("index.html")
#     return HTMLResponse(content=template.render())

@app.get("/")
async def home_page():
    """
    Render the home page with a simple message.
    """
    return JSONResponse(content={"message": "Welcome to the Semantic Kernel Orchestrator API!"})

# Define the chat endpoint
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    orchestrator = app.state.orchestrator
    response = await orchestrator.process_message(request.message)
    return {"response": response}
