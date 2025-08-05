# Azure Language OpenAI Conversational Agent Accelerator
| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator) |
|---|---|

This accelerator template provides users with a code-first example for creating and enhancing chat solutions and agents with deterministic, human-controllable workflows. It is designed to minimize the need for extensive prompt engineering by using a structured workflow to prioritize top questions with exact answers, top intents with deterministic routing, and use LLM to handle long tail topics. These actions help to ensure determinism and consistency. The template also provides flexibility to swap, add, or remove agents/components to tailor to your specific needs.

This template is perfect for developers and organizations looking to design, customize, and manage agents that can handle complex queries, route tasks, and provide reliable answers, all with a controlled, scalable architecture.


### MENU: [**FEATURES**](#features) • [**AGENT ARCHITECTURE**](#agent-architecture) • [**GETTING STARTED**](#getting-started) • [**GUIDANCE**](#guidance)

## Important Security Notice

This template, the application code and configuration it contains, have been built to showcase Microsoft Azure specific services and tools. We strongly advise our customers not to make this code part of their production environments without implementing or enabling additional security features.

## Features

This solution leverages the combined capabilities of Azure AI Language, Azure AI Agent Service and Azure OpenAI for enhanced conversational agent solutions. The following image is a reference architecture diagram of this Agent template.

![image](./docs/images/sk_flow_translate.png)

1. **Client-Side User Interface:** A web-based client-side user interface allows you to quickly explore and test this Agent template.
2. **Orchestrator:** The orchestrator allows for a dynamic, adaptable workflow with multiple orchestration options including utilizing Semantic Kernel's group chat orchestration with an intent routing agent (based on [this template](https://github.com/azure-ai-foundry/foundry-samples/tree/main/samples/agent-catalog/msft-agent-samples/foundry-agent-service-sdk/intent-routing-agent)) as the manager agent to moderate and route the conversation, LLM function calling, CLU for intent identification only and CQA for returning exact pre-set answers only, etc. Both intent routing agent and LLM function calling options leverages CLU and CQA to provide high-quality intent identficiation and exact question-answering. See the routing strategies section down below for more details between these options. 
3. **Conversational Language Understanding (CLU):** CLU enables you to define the top intents to ensure response quality. Whether completing a task or addressing specific customer needs, CLU provides a mechanism to ensure the agent accurately understands and executes the process of handling predefined intents. You can update the top intents as necessary to accommodate evolving business needs. Check out [the CLU product documents](https://learn.microsoft.com/azure/ai-services/language-service/conversational-language-understanding/overview) for more details.
4. **Custom Question Answering (CQA):** CQA allows you to create and manage predefined QA pairs to deliver precise responses. CQA can respond consistently, improving reliability, particularly for high-stakes or regulatory-sensitive conversations. You can update the predefined QA pairs as needed to match your growing business needs. Check out [the CQA product documents](https://learn.microsoft.com/azure/ai-services/language-service/question-answering/overview) for more details.
5. **PII Detection and Redaction (PII):** Protecting user privacy is a top priority. Azure AI Language’s Personally Identifiable Information (PII) can identify and redact sensitive information before sending to LLM for processing. Check out [the PII product documents](https://learn.microsoft.com/azure/ai-services/language-service/personally-identifiable-information/overview?tabs=text-pii) for more details.
6. **Large Language Model with Retrieval-Augmented Generation (LLM with RAG) to Handle Everything Else:** In this template, we are showcasing a RAG solution using Azure AI Search to handle missed intents or user queries on lower-priority topics. This RAG solution can be replaced with your existing one.  
7. **Template Configuration for "Plug-and-Play":** The template is designed to allow you to easily swap, add, or remove components to tailor to your specific needs. Whether you want to add custom intents, adjust fallback mechanisms, or incorporate additional data sources, the modular nature of this template makes it simple to configure.

### Benefits
Azure AI Language already offers two services: Conversational Language Understanding (CLU) and Custom Question Answering (CQA). CLU analyzes user inputs to extract intents and entities. CQA uses pre-defined question-answer pairs or a pre-configured knowledgebase to answer user questions.
#### How CLU can help
A common issue with intent prediction in conversational AI is the misclassification of user intents and inaccurate entity identification. This can lead to poor user experience due to inaccurately invoked AI Agents or custom actions for intent fulfillment.  

CLU can help by performing easy-to-configure and intuitive model training to map utterances to newly added pre-defined intents with high confidence. The recognition is through natural language, not hard-coded for natural interaction with users. This ensures that the system can handle inputs gracefully, provide more accurate responses, and achieve fast and low-cost intent classification.

By leveraging CLU, users can enhance their conversational AI solutions, improve intent predication accuracy, making it a valuable agent/workflow routing solution.
#### How CQA can help
A typical RAG solution allows users to chat with an AI agent and obtain grounded responses. Chat messages are sent directly to AOAI, where a specified model (e.g. GPT-4o) processes each message and creates a response. This is beneficial when customers have their own grounding data (e.g. product manuals, company information for Q/A). They would set up an Azure AI Search index to query their grounding data, and preprocess user chat messages by fetching relevant grounding data and passing it to the AOAI model downstream. Because the model now "knows" the grounding data to base its response around, user chats are met with contextual responses, improving the chat experience.

However, issues with RAG solutions (DSATs, or dissatisfactory examples) are hard to address. It is difficult to debug or update grounding data to fix inaccurate "grounded" responses. Further, this process can be expensive and time-consuming

Azure AI Language CQA can help address these issues and expand the functionality of existing RAG chat solutions. 

## Agent Architecture
![image](./docs/images/architecture.png)
This project includes a `UnifiedConversationOrchestrator` class that unifies the call to different routing strategies, which can intelligently route user input to intent routing agent, CLU-only, CQA-only, etc., based on the specified router type. 

The intent routing agent is implemented with Semantic Kernel's group chat orchestration. It uses `CLU` and `CQA` as tools to predict intents based on your custom intents defined in `CLU` and answer FAQs if the corresponding question-answer pairs are created in `CQA`. In this orchestration, the intent routing agent takes the manager agent role to moderate and route the user queries to other appropriate agents as needed based on the results from `CLU` and `CQA`. 

There is also fallback functionality when any of the following occurs: neither runtime is called, API call failed, confidence threshold not met, `CLU` did not recognize an intent, or `CQA` failed to answer the question. This fallback functionality can be configured to be any function. In this user-story, fallback will be the original `RAG` solution. The orchestrator object takes a string message as input, and outputs a dictionary object containing information regarding what runtime was called, relevant outputs, was fallback called, etc.

When combined with an existing `RAG` solution, adding a `UnifiedConversationOrchestrator` can help in the following ways:
- Use `CQA` to quick fix and override incorrect answers from `RAG` solution.
- Extended chat functionality based on recognized intents/entities using `CLU`.
- Consistent fallback to original chat functionality with `RAG`.
Further, users can provide their own business logic to call based on `CLU` results (e.g. with an `OrderStatus` intent and `OrderId` entity, user can include business logic to query a database to check the order status).

The container instance demo included with this project showcases the following chat experience:
- User inputs chat dialog.
- AOAI node preprocesses by breaking input into separate utterances.
- Orchestrator routes each utterance to either an intent routing agent (with `CLU` and `CQA`), LLM function calls, directly fallback `RAG`, etc., based on your routing strategy value assigned to `router_type` in `server.py` (all valid routing strategy values are listed in the "Routing strategies" section below).
- If an intent defined in `CLU` was predicted, call extended business agent/logic based on intent/entities.
- Agent summarizes response (what business action was performed, provide answer to question, provide grounded response).

### Use Case
Consider the following real-world example: Contoso Outdoors, a fictional retail company, has an existing RAG chat solution using AOAI. Their grounding data is composed of product manuals of the outdoor gear they sell. Because of this, users can easily ask the AI chat questions regarding Contoso Outdoors products (e.g. What tents do you sell?) and obtain grounded, contextual, and accurate responses.

However, if a user asks questions about the company's return policy, or something misclassified to grounding data, the RAG chat will not be able to respond accurately, as the grounding data does not contain any information regarding a return policy. It can be expensive and time consuming to update the grounding data to address this. Further, if a user asks a question about their online order status, even with updates of grounding data, RAG is not able to respond effectively here, as information is dynamic.

Incorporating CLU/CQA (through an intent routing agent or LLM function calls) using a UnifiedConversationOrchestrator solves these problems. Contoso Outdoors would set up a CQA model that can answer extended questions (e.g. their return policy), and set up a CLU model that can identify online order actions (e.g. checking the status of an order). Now, both of these DSATs are resolved, and Contoso Outdoors still maintains their existing RAG chat functionality, as UnifiedConversationOrchestrator falls back to the original RAG chat if CLU/CQA are not fit to respond to the user chat.

![image](./docs/images/ui.png)

This displays the "better together" story when using Azure AI Language with Azure AI Agent Service and/or Azure OpenAI to provide a deterministic conversational agent experience. Learn more about related offerings from this blog post: [Announcing Azure AI Language new features to accelerate your agent development](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/announcing-azure-ai-language-new-features-to-accelerate-your-agent-development/4415216).

## Notes:
**GenAI is used in the following contexts:**
- Demo code: General AOAI GPT chat client to break user inputs into separate utterances.
- Demo code: General AOAI GPT `RAG` client to provide grounded responses as a fallback function.
- Orchestrator: one routing option uses AOAI GPT function-calling to decide whether to call `CLU` or `CQA` runtimes, and another option that uses an intent routing agent with `CLU` and `CQA` as tools.

**Sample Data:** This project includes sample data to create project dependencies. Sample data is in the context of a fictional outdoor product company: Contoso Outdoors.

**Routing strategies:**
- `TRIAGE_AGENT`: Route to an intent routing agent that uses `CLU` and `CQA` as tools.
- `FUNCTION_CALLING`: Route to either `CLU` or `CQA` runtime using AOAI GPT function-calling to decide.
- `CLU`: Route to `CLU` runtime only.
- `CQA`: Route to `CQA` runtime only.
- `ORCHESTRATION`: Route to either `CQA` or `CLU` runtime using an Azure AI Language [Orchestration](https://learn.microsoft.com/en-us/azure/ai-services/language-service/orchestration-workflow/overview) project to decide.
- `BYPASS`: No routing. Only call fallback function.

In any case, the fallback function is called if routing "failed". `CLU` route is considered "failed" is confidence threshold is not met or no intent is recognized. `CQA` route is considered "failed" if confidence threhsold is not met or no answer is found. `TRIAGE_AGENT`, `FUNCTION_CALLING` and `ORCHESTRATION` route depend on the return value of the runtime they call.

## Getting Started

<h3><img src="./docs/images/quick_deploy.png" width="64">
<br/>
QUICK DEPLOY
</h3>

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator) |
|---|---|

### **Prerequisites**
To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups and resources** as well as being able to create role assignments. Follow the steps in  [Azure Account Set Up](./docs/azure_account_set_up.md). We recommend you have `Owner` permissions on the subscription you are deploying this template to (though more minimal permissions will suffice as well).

### Region Selection
The following regions should support all Azure dependencies (except possibly AOAI model support) for this template:
- `australiaeast`
- `centralindia`
- `eastus`
- `eastus2`
- `northeurope`
- `southcentralus`
- `switzerlandnorth`
- `uksouth`
- `westeurope`
- `westus2`
- `westus3`

For best latency performance, we recommend you choose a region close to your physical geography.

### **Configurable Deployment Settings**

| **Setting** | **Description** |  **Default value** |
|------------|----------------|  ------------|
| **GPT Model Name** | `gpt-4o` or `gpt-4o-mini` | `gpt-4o-mini` |  
| **GPT Model Deployment Capacity** | Configure capacity for **GPT model deployment** | `100k` |
| **GPT Deployment Type** | `GlobalStandard` or `Standard` |  `GlobalStandard` |
| **Embedding Model name** | `text-embedding-ada-002` or `text-embedding-3-small` | `text-embedding-ada-002` |
| **Embedding Model Capacity** | Configure capacity for **embedding model deployment** |  `100k` |
| **Embedding Deployment Type** | `GlobalStandard` or `Standard` |  `GlobalStandard` |

The models, deployment types, and capacities you choose may depend on the region you select. To help you in choosing what is available in your subscription, please run the helper script:
```
az login
source infra/setup_azd_parameters.sh
```
This will populate the above deployment settings based on your selections. The script will automatically be run when you deploy through GitHub Codespaces or VS Code Dev Containers. When you finally run `azd up`, ensure you are choosing the same region you selected here.

### [Optional] Quota Recommendations
For demo/test purposes, we recommend model deployment capacities to be **20k tokens**. This small value ensures an adequate testing/demo experience, but is not meant for production workloads.  
> **We recommend increasing the capacity for optimal performance under large loads.**

**⚠️ Warning:**  **Insufficient quota can cause deployment errors.** Please ensure you have the recommended capacity or request for additional capacity before deploying this solution.

### Deployment Options
Pick from the options below to see step-by-step instructions for: GitHub Codespaces, VS Code Dev Containers, Local Environments, and Bicep deployments.

<details>
  <summary><b>Deploy in GitHub Codespaces</b></summary>

### GitHub Codespaces

You can run this solution using GitHub Codespaces. The button will open a web-based VS Code instance in your browser:

1. Open the solution accelerator (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator)

2. Accept the default values on the create Codespaces page.
3. Open a terminal window if it is not already open.
4. Follow the instructions in the helper script to populate deployment variables.
5. Continue with the [deploying steps](#deploying).

</details>

<details>
  <summary><b>Deploy in VS Code</b></summary>

 ### VS Code Dev Containers

You can run this solution in VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it, if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator)


3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Follow the instructions in the helper script to populate deployment variables.
5. Continue with the [deploying steps](#deploying).

</details>

<details>
  <summary><b>Deploy in your local environment</b></summary>

 ### Local environment

If you're not using one of the above options for opening the project, then you'll need to:

1. Make sure the following tools are installed:

    * `bash`
    * [Azure Developer CLI (azd)](https://aka.ms/install-azd)

2. Download the project code:

    ```shell
    azd init -t Azure-Samples/Azure-Language-OpenAI-Conversational-Agent-Accelerator/
    ```
    **Note:** the above command should be run in a new folder of your choosing. You do not need to run `git clone` to download the project source code. `azd init` handles this for you.

3. Open the project folder in your terminal or editor.
4. Run the helper script to populate deployment variables: 
```
az login
source infra/setup_azd_parameters.sh
```
5. Continue with the [deploying steps](#deploying).

</details>

### Deploying

Once you've opened the project in [Codespaces](#github-codespaces) or in [Dev Containers](#vs-code-dev-containers) or [locally](#local-environment), you can deploy it to Azure following the following steps. 

To change the `azd` parameters from the default values, follow the steps [here](./docs/customizing_azd_parameters.md). 


1. Login to Azure:

    ```shell
    azd auth login
    ```

2. Provision and deploy all the resources:

    ```shell
    azd up
    ```

3. Provide an `azd` environment name (like "conv-agent")
4. Select a subscription from your Azure account, and select a location which has quota for all the resources. 
    * This deployment will take *10-15 minutes* to provision the resources in your account and set up the solution with sample data.

      > **Tip:** A link to view the deployment's detailed progress in the Azure Portal shows up in your terminal window. You can open this link to see the deployment progress and go to the resource group.
    
    * If you get an error or timeout with deployment, changing the location can help, as there may be availability constraints for the resources.

5. Once the deployment has completed successfully, **wait a few minutes (~5) to let the app finish setting up dependencies**. Then, open the [Azure Portal](https://portal.azure.com/), go to the deployed resource group, find the Container Group resource (`cg-<unique-identifier>`) and get the app URL from `FQDN`.

6. Test the app locally with the sample question: _What is your return policy?_. For more sample questions you can test in the application, see [Sample Questions](#sample-questions).

    6a. If you are encountering issues viewing the web app, try waiting a few more minutes for the app to set up. If you still have issues, view the container logs of the Container Group resource in the Azure Portal. Make sure to include this information when opening any issues on the template.

7. You can now delete the resources by running `azd down`, if you are done trying out the application. 
<!-- 6. You can now proceed to run the [development server](#development-server) to test the app locally, or if you are done trying out the app, you can delete the resources by running `azd down`. -->

### Additional Steps

1. **Limit Access to your App**

    Follow the discussion [here](https://learn.microsoft.com/en-us/answers/questions/319407/how-to-limit-access-to-a-container-running-in-cont) to run your app in a Virtual Network and limit access.

2. **Deleting Resources After a Failed Deployment**

    Follow steps in [Delete Resource Group](./docs/delete_resource_group.md) If your deployment fails and you need to clean up the resources.

2. **Updating Example Data**

    If you wish to update the existing example project data, you can do so by updaing the files in `infra/data/`:
    - update the intents, entities, and utterances in `clu_import.json` to modify the app's CLU project.
    - update the questions and answers in `cqa_import.json` to modify the app's CQA project.
    - update the files in `product_info.tar.gz` to modify the grounding data the app uses to populate a search index for `RAG`.

    If you update these files, ensure that you reference new project/index names in `infra/resources/container_group.bicep`:
    - update `param clu_project_name` if you updated CLU data.
    - update `param cqa_project_name` if you updated CQA data.
    - update `param orchestration_project_name` if you updated CLU or CQA data.
    - update `param search_index_name` if you updated grounding data.

    When updating example data, ensure that it adheres to [RAI guidelines](#responsible-ai-transparency-faq). Run `azd up` again to update the web app.

### Sample Questions

To help you get started, here are some **Sample Questions** you can ask in the app:

- What is your return policy?
- What is the status of order 12?
- What tents are recommended for winter?
- What boots do you sell?

## Guidance

### Responsible AI Transparency FAQ 

Please refer to [Transparency FAQ](./RAI_FAQ.md) for responsible AI transparency details of this solution accelerator.

### Costs

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage.
The majority of the Azure resources used in this infrastructure are on usage-based pricing tiers.
However, Azure Container Registry has a fixed cost per registry per day.

You can try the [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator) for the resources:

* Azure AI Search: Standard tier, S1. Pricing is based on the number of documents and operations. [Pricing](https://azure.microsoft.com/pricing/details/search/)
* Azure Storage Account: Standard tier, LRS. Pricing is based on storage and operations. [Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/)
* Azure OpenAI: S0 tier, defaults to gpt-4o-mini and text-embedding-ada-002 models. Pricing is based on token count. [Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/?msockid=3d25d5a7fe346936111ec024ff8e685c)
* Azure Container Instances: Pay as you go. Container has default settings of 1 vCPU and 1 GB. [Pricing](https://azure.microsoft.com/en-us/pricing/details/container-instances/?msockid=3d25d5a7fe346936111ec024ff8e685c)
* Azure AI Language: S tier. [Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/language-service/?msockid=3d25d5a7fe346936111ec024ff8e685c)


⚠️ To avoid unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.

### Security
This template uses [Managed Identity](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) to eliminate the need for developers to manage credentials.

To ensure continued best practices in your own repository, we recommend that anyone creating solutions based on our templates ensure that [Github secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) setting is enabled.

You may want to consider additional security measures, such as:

* Enabling Microsoft Defender for Cloud to [secure your Azure resources](https://learn.microsoft.com/azure/security-center/defender-for-cloud).
* Protecting the Azure Container Instance with a [firewall](https://learn.microsoft.com/azure/container-apps/waf-app-gateway) and/or [Virtual Network](https://learn.microsoft.com/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli).

## Resources
Supporting documentation:
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/) 
- [Azure Container Instances](https://learn.microsoft.com/en-us/azure/container-instances/)
- [Azure AI Language](https://learn.microsoft.com/en-us/azure/ai-services/language-service/overview)
- [CLU](https://learn.microsoft.com/en-us/azure/ai-services/language-service/conversational-language-understanding/overview)
- [CQA](https://learn.microsoft.com/en-us/azure/ai-services/language-service/question-answering/overview)

## Disclaimers
To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, “Microsoft Products and Services”), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services. 

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit https://aka.ms/exporting. 

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer’s implementation of the Online Services. 

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.  

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, “HIGH-RISK USE”), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.  

##  Trademarks: 
This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

## Data Collection:
The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.

**Note**: 
- No telemetry or data collection is directly added in this accelerator project. Please review individual telemetry information from the included Azure services (e.g. Azure AI Language, Azure OpenAI etc.) regarding their APIs.
