from application.app import app
import os
from azure.identity import DefaultAzureCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from urllib.parse import unquote, urlparse
from typing import List, Dict

@app.function_name(name="document_cracking")
@app.activity_trigger(input_name="bloburl")
def document_cracking(bloburl: str) -> Dict:
    endpoint = os.getenv("DI_ENDPOINT")
    key = os.getenv("DI_KEY")  # Put your access key here

    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    poller = client.begin_analyze_document("prebuilt-layout", AnalyzeDocumentRequest(url_source=bloburl))
    result: AnalyzeResult = poller.result()

    # Get the number of pages in the document
    num_pages = len(result.pages)
    
    # Initialize an array to store content for each page
    page_contents = [""] * num_pages
    
    # Extract text from each page
    for i, page in enumerate(result.pages):
        page_contents[i] = "".join([line['content'] for line in page.lines])
    
    # Process tables and place them in their corresponding pages
    if result.tables:
        for table in result.tables:
            # Determine which page the table belongs to (using the first cell's page number)
            if table.cells and hasattr(table.cells[0], 'bounding_regions') and table.cells[0].bounding_regions:
                table_page_num = table.cells[0].bounding_regions[0].page_number - 1  # Convert to 0-based index
                
                # Create a formatted representation of the table
                table_text = []
                
                # Create a 2D array to store the table cells
                rows = max(cell.row_index for cell in table.cells) + 1
                cols = max(cell.column_index for cell in table.cells) + 1
                table_array = [['' for _ in range(cols)] for _ in range(rows)]
                
                # Fill in the array with cell content
                for cell in table.cells:
                    row_idx = cell.row_index
                    col_idx = cell.column_index
                    table_array[row_idx][col_idx] = cell.content
                
                # Format table as text
                table_text.append("\n--- TABLE START ---")
                for row in table_array:
                    table_text.append(" | ".join(row))
                table_text.append("--- TABLE END ---\n")
                
                # Add the table to the appropriate page
                if 0 <= table_page_num < num_pages:
                    page_contents[table_page_num] += "\n" + "\n".join(table_text)
    
    return {
        "pages": page_contents,
        "url": bloburl,
        "filename": unquote(urlparse(bloburl)[2].split("/")[-1])
    }