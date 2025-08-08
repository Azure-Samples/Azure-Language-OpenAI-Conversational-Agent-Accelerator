import re
import os
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential


def bind_parameters(input_string: str, parameters: dict) -> str:
    """
    Replace occurrences of '${key}' in the input string with the value of the key in the parameters dictionary.

    :param input_string: The string containing keys of value to replace.
    :param parameters: A dictionary containing the values to substitute in the input string.
    :return: The modified string with parameters replaced.
    """
    if parameters is None:
        return input_string

    # Define the regex pattern to match '${key}'
    parameter_binding_regex = re.compile(r"\$\{([^}]+)\}")

    # Replace matches with corresponding values from the dictionary
    return parameter_binding_regex.sub(
        lambda match: parameters.get(match.group(1), match.group(0)),
        input_string
    )


def get_azure_credential():
    use_mi_auth = os.environ.get('USE_MI_AUTH', 'false').lower() == 'true'

    if use_mi_auth:
        mi_client_id = os.environ['MI_CLIENT_ID']
        return ManagedIdentityCredential(
            client_id=mi_client_id
        )

    return DefaultAzureCredential()
