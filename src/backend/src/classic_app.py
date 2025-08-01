# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import importlib
import pii_redacter
from json import JSONDecodeError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from azure.search.documents import SearchClient
from aoai_client import AOAIClient, get_prompt
from router.router_type import RouterType
from unified_conversation_orchestrator import UnifiedConversationOrchestrator
from utils import get_azure_credential


DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist"))
# log dist_dir
print(f"DIST_DIR: {DIST_DIR}")


# FastAPI app:
app = FastAPI()
app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")


# RAG AOAI client:
search_client = SearchClient(
    endpoint=os.environ.get("SEARCH_ENDPOINT"),
    index_name=os.environ.get("SEARCH_INDEX_NAME"),
    credential=get_azure_credential()
)


rag_client = AOAIClient(
    endpoint=os.environ.get("AOAI_ENDPOINT"),
    deployment=os.environ.get("AOAI_DEPLOYMENT"),
    use_rag=True,
    search_client=search_client
)


# Extract-utterances AOAI client:
extract_prompt = get_prompt("extract_utterances.txt")
extract_client = AOAIClient(
    endpoint=os.environ.get("AOAI_ENDPOINT"),
    deployment=os.environ.get("AOAI_DEPLOYMENT"),
    system_message=extract_prompt
)


# PII:
PII_ENABLED = os.environ.get("PII_ENABLED", "false").lower() == "true"


# Fallback function (RAG):
def fallback_function(
    query: str,
    language: str,
    id: int
) -> str:
    """
    Call RAG client for grounded chat completion.
    """
    if PII_ENABLED:
        # Redact PII:
        query = pii_redacter.redact(
            text=query,
            id=id,
            language=language,
            cache=True
        )

    return rag_client.chat_completion(query)


# Unified-Conversation-Orchestrator:
router_type = RouterType(os.environ.get("ROUTER_TYPE", "BYPASS"))
orchestrator = UnifiedConversationOrchestrator(
    router_type=router_type,
    fallback_function=fallback_function
)
chat_id = 0


def orchestrate_chat(message: str) -> list[str]:
    if PII_ENABLED:
        # Redact PII:
        message = pii_redacter.redact(
            text=message,
            id=chat_id,
            cache=True
        )

    # Break user message into separate utterances:
    utterances = extract_client.chat_completion(message)
    print(f"Utterances: {utterances}")
    if not isinstance(utterances, list):
        try:
            utterances = json.loads(utterances)
        except JSONDecodeError:
            # Harmful content case:
            if PII_ENABLED:
                # Clean up PII memory:
                pii_redacter.remove(id=chat_id)
            return ['I am unable to respond or participate in this conversation.']

    # Process each utterance:
    responses = []
    for query in utterances:
        if PII_ENABLED:
            # Reconstruct PII:
            query = pii_redacter.reconstruct(
                text=query,
                id=chat_id,
                cache=True
            )

        # Orchestrate:
        orchestration_response = orchestrator.orchestrate(
            message=query,
            id=chat_id
        )

        # Parse response:
        response = None
        if orchestration_response["route"] == "fallback":
            response = orchestration_response["result"]

        elif orchestration_response["route"] == "clu":
            intent = orchestration_response["result"]["intent"]
            entities = orchestration_response["result"]["entities"]

            # Here, you may call external functions based on recognized intent:
            hooks_module = importlib.import_module("clu_hooks")
            hook_func = getattr(hooks_module, intent)
            response = hook_func(entities)

        elif orchestration_response["route"] == "cqa":
            answer = orchestration_response["result"]["answer"]
            response = answer

        print(f"Orchestration response: {orchestration_response}")
        print(f"Parsed response: {response}")
        responses.append(response)

    if PII_ENABLED:
        # Clean up PII memory:
        pii_redacter.remove(id=chat_id)

    return responses


@app.get("/", response_class=HTMLResponse)
async def home_page():
    """Serve the index.html page."""
    with open("dist/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/chat")
async def chat(request: Request):
    content = await request.json()
    message = content["message"]

    responses = orchestrate_chat(message)

    print(f"responses: {responses}")
    return JSONResponse({
        "messages": responses
    })
