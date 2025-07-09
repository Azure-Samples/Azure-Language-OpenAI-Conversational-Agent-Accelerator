# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import re
from azure.identity import AzureCliCredential
from azure.ai.language.conversations.authoring import ConversationAuthoringClient
from azure.ai.language.questionanswering.authoring import AuthoringClient
from azure.core.rest import HttpRequest

IS_GITHUB_WORKFLOW_RUN = os.environ.get('IS_GITHUB_WORKFLOW_RUN', 'false').lower() == 'true'


def camel_to_snake(camel_str):
    # Insert underscores before capital letters and convert to lowercase
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    return snake_str


def bind_parameters(input_string: str, parameters: dict) -> str:
    """
    Replace occurrences of '${<key>}' in the input string.

    Replace with value of <key> in `parameters`.
    If <key> does not exist in `parameters`, check for env var.
    If <key> does not exist as an env var, perform no replacement.
    """
    def replacer(match):
        key = match.group(1)
        return str(parameters.get(key, os.environ.get(key, match.group(0))))

    pattern = re.compile(r'\$\{([^}]+)\}')
    return pattern.sub(replacer, input_string)


def get_clu_intents() -> list[str]:
    """
    Get all intents registered in CLU project.
    """
    project_name = os.environ['CLU_PROJECT_NAME']
    client = ConversationAuthoringClient(
        endpoint=os.environ['LANGUAGE_ENDPOINT'],
        credential=AzureCliCredential()
    )

    try:
        print(f'Getting intents from CLU project {project_name}...')

        poller = client.begin_export_project(
            project_name=project_name,
            string_index_type='Utf16CodeUnit',
            exported_project_format='Conversation'
        )

        job_state = poller.result()
        request = HttpRequest('GET', job_state['resultUrl'])
        response = client.send_request(request)
        exported_project = response.json()

        intents = [
            i['category'] for i in exported_project['assets']['intents']
        ]
        intents = list(filter(lambda x: x != 'None', intents))
        return intents

    except Exception as e:
        print(f'Unable to get intents: {e}')
        raise e


def get_cqa_questions() -> list[str]:
    """
    Get all registered questions in CQA project.
    """
    project_name = os.environ['CQA_PROJECT_NAME']
    client = AuthoringClient(
        endpoint=os.environ['LANGUAGE_ENDPOINT'],
        credential=AzureCliCredential()
    )

    if IS_GITHUB_WORKFLOW_RUN:
        # Due to auth issues when running in GitHub workflow, skip:
        print('Skipping CQA project polling...')
        return []

    try:
        print(f'Getting questions from CQA project {project_name}...')

        poller = client.begin_export(
            project_name=project_name,
            file_format='json'
        )

        job_state = poller.result()
        request = HttpRequest('GET', job_state['resultUrl'])
        response = client.send_request(request)
        exported_project = response.json()

        questions = set()
        for item in exported_project['Assets']['Qnas']:
            for q in item['Questions']:
                questions.add(q)
        return list(questions)

    except Exception as e:
        print(f'Unable to get questions: {e}')
        raise e
