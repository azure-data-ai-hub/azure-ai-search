# list_blobs_chunk_activity.py

import azure.functions as func
import azure.durable_functions as df
from azure.storage.blob import BlobServiceClient
import os
from application.app import app
from azure.identity import DefaultAzureCredential
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from urllib.parse import quote
import datetime

@app.function_name(name="list_blobs_chunk")
@app.activity_trigger(input_name="params")
def list_blobs_chunk(params: dict):
    container_name = params.get("container_name")
    continuation_token = params.get("continuation_token")
    prefix_list_offset = params.get("prefix_list_offset", 0)
    chunk_size = params.get("chunk_size", 5000)
    prefix_list = params.get("prefix_list")
    
    if len(prefix_list) <= prefix_list_offset:
        return {
            "blob_names": [],
            "continuation_token": None,
            "prefix_list_offset": prefix_list_offset
        }

    # Use connection string from Application Settings (local.settings.json for local dev)
    source_connection_string = os.getenv("SOURCE_STORAGE_CONNECTION_STRING")
    source_blob_service_client = BlobServiceClient.from_connection_string(source_connection_string)
    container_client = source_blob_service_client.get_container_client(container_name)

    # List blobs in a segment (page) using a continuation token
    blob_urls = []
    result_segment = container_client.list_blobs(name_starts_with=prefix_list[prefix_list_offset], results_per_page=chunk_size)
    
    source_account_name = os.getenv("SOURCE_STORAGE_ACCOUNT_NAME")

    new_continuation_token = None
    pages = result_segment.by_page(continuation_token=continuation_token)
    for page in pages:
        for blob in page:
            sas_token = generate_blob_sas(
                account_name=source_account_name,
                container_name=container_name,
                account_key=os.getenv("SOURCE_STORAGE_ACCOUNT_KEY"),
                blob_name=blob.name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
            )
            blob_urls.append(
                f"https://{source_account_name}.blob.core.windows.net/{container_name}/{quote(blob.name)}?{sas_token}"
            )
        new_continuation_token = pages.continuation_token
        if not new_continuation_token:
            prefix_list_offset += 1
        break

    return {
        "blob_names": blob_urls,
        "continuation_token": new_continuation_token,
        "prefix_list_offset": prefix_list_offset
    }
