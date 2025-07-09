# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
from azure.identity import AzureCliCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndex,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SplitSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    AzureOpenAIEmbeddingSkill,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    IndexProjectionMode,
    SearchIndexerSkillset,
    SearchIndexer,
    FieldMapping
)


aoai_endpoint = os.environ['AOAI_ENDPOINT']
embedding_deployment_name = os.environ['EMBEDDING_DEPLOYMENT_NAME']
embedding_model_name = os.environ['EMBEDDING_MODEL_NAME']
embedding_model_dimensions = int(os.environ['EMBEDDING_MODEL_DIMENSIONS'])

storage_account_connection_string = os.environ['STORAGE_ACCOUNT_CONNECTION_STRING']
blob_container_name = os.environ['BLOB_CONTAINER_NAME']

index_name = os.environ['SEARCH_INDEX_NAME']
data_source_name = index_name + '-ds'
skillset_name = index_name + '-ss'
indexer_name = index_name + '-idxr'

endpoint = os.environ['SEARCH_ENDPOINT']
credential = AzureCliCredential()

# Search index:
index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
fields = [
    SearchField(name="parent_id", type=SearchFieldDataType.String),
    SearchField(name="title", type=SearchFieldDataType.String),
    SearchField(name="chunk_id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True, analyzer_name="keyword"),
    SearchField(name="chunk", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
    SearchField(name="text_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), vector_search_dimensions=embedding_model_dimensions, vector_search_profile_name="hnswSearch")
    ]

# Vector search configuration:
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(name="hnswConfig"),
    ],
    profiles=[
        VectorSearchProfile(
            name="hnswSearch",
            algorithm_configuration_name="hnswConfig",
            vectorizer_name="aoaiVec",
        )
    ],
    vectorizers=[
        AzureOpenAIVectorizer(
            vectorizer_name="aoaiVec",
            kind="azureOpenAI",
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=aoai_endpoint,
                deployment_name=embedding_deployment_name,
                model_name=embedding_model_name
            )
        )
    ]
)

# Create search index:
index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
result = index_client.create_or_update_index(index)
print(f"{result.name} created")

# Create data source:
indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
container = SearchIndexerDataContainer(name=blob_container_name)
data_source_connection = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=storage_account_connection_string,
    container=container
)
data_source = indexer_client.create_or_update_data_source_connection(data_source_connection)

print(f"Data source '{data_source.name}' created or updated")

# Chunking:
split_skill = SplitSkill(  
    description="Split skill to chunk documents",
    text_split_mode="pages",
    context="/document",
    maximum_page_length=2000,
    page_overlap_length=500,
    inputs=[
        InputFieldMappingEntry(name="text", source="/document/content"),
    ],
    outputs=[
        OutputFieldMappingEntry(name="textItems", target_name="pages")
    ]
)

# Embedding:
embedding_skill = AzureOpenAIEmbeddingSkill(
    description="Skill to generate embeddings via Azure OpenAI",
    context="/document/pages/*",
    resource_url=aoai_endpoint,
    deployment_name=embedding_deployment_name,
    model_name=embedding_model_name,
    dimensions=embedding_model_dimensions,
    inputs=[
        InputFieldMappingEntry(name="text", source="/document/pages/*"),
    ],
    outputs=[
        OutputFieldMappingEntry(name="embedding", target_name="text_vector")
    ]
)

# Projections:
index_projections = SearchIndexerIndexProjection(
    selectors=[
        SearchIndexerIndexProjectionSelector(
            target_index_name=index_name,
            parent_key_field_name="parent_id",
            source_context="/document/pages/*",
            mappings=[
                InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
                InputFieldMappingEntry(name="text_vector", source="/document/pages/*/text_vector"),
                InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),
            ],
        ),
    ],
    parameters=SearchIndexerIndexProjectionsParameters(
        projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
    )
)

# Create skillset:
skills = [split_skill, embedding_skill]
skillset = SearchIndexerSkillset(
    name=skillset_name,
    description="Skillset to chunk documents and generating embeddings",
    skills=skills,
    index_projection=index_projections,
)

client = SearchIndexerClient(endpoint=endpoint, credential=credential)
client.create_or_update_skillset(skillset)
print(f"{skillset.name} created")

# Create indexer:
indexer_parameters = None

indexer = SearchIndexer(
    name=indexer_name,
    description="Indexer to index documents and generate embeddings",
    skillset_name=skillset_name,
    target_index_name=index_name,
    data_source_name=data_source.name,
    # Map metadata_storage_name field to title field in index to display PDF title in search results:
    field_mappings=[FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")],
    parameters=indexer_parameters
)

# Create and run indexer:
indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
indexer_result = indexer_client.create_or_update_indexer(indexer)

print(f"{indexer_name} is created and running. Give the indexer a few minutes before running a query.")
