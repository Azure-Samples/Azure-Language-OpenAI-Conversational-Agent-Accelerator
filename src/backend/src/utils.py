# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
from azure.identity import AzureCliCredential, ManagedIdentityCredential


def get_azure_credential():
    use_mi_auth = os.environ.get('USE_MI_AUTH', 'false').lower() == 'true'

    if use_mi_auth:
        mi_client_id = os.environ['MI_CLIENT_ID']
        return ManagedIdentityCredential(
            client_id=mi_client_id
        )

    return AzureCliCredential()
