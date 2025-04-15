from application.app import app
import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from typing import List, Dict

@app.function_name(name="embedding")
@app.activity_trigger(input_name="chunks")
def embedding(chunks: List[Dict]) -> List[Dict]:
    endpoint = os.getenv("AOPENAI_ENDPOINT")
    api_key = os.getenv("AOPENAI_API_KEY")

    # Use key-based auth instead of token-based auth
    client = AzureOpenAI(
        api_version="2024-02-15-preview",
        azure_endpoint=endpoint,
        api_key=api_key
    )

    embeddings = client.embeddings.create(
        input=[chunk["text"] for chunk in chunks],
        model="text-embedding-3-large"
    )
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings.data[i].embedding
    return chunks