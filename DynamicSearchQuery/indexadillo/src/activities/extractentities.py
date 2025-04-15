from application.app import app
from typing import List, Dict
import re
import logging

logger = logging.getLogger("scripts")

@app.function_name(name="extract_entities")
@app.activity_trigger(input_name="chunks")
def extractentities(chunks: List[Dict]) -> List[Dict]:

    logger.info("Extracting entities from chunks with embeddings")
    logger.info(f"Number of chunks in the document: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        # This pattern matches zip codes like 12345 or 12345-6789, even if directly followed by letters (no space).
        zipcodes = re.findall(r'\b(\d{5}(?:-\d{4})?)\b', chunk["text"])
        chunk["zipcodes"] = zipcodes

        # Extract domains (e.g. example.com, sub.domain.org)
        domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}\b', chunk["text"])
        chunk["domains"] = domains

        # Extract URLs with http:// or https://
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', chunk["text"])
        chunk["urls"] = urls

        # Broader phone number pattern to include more formats
        phone_pattern = r'\b(?:\+?\d{1,3}[\s.-]?)?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b'
        phonenumbers = re.findall(phone_pattern, chunk["text"])
        chunk["phonenumbers"] = phonenumbers

        # Extract email addresses - improved pattern to handle more formats
        # This will match standard emails, emails in parentheses, and emails with "(at)" notation
        emails = re.findall(r'\b[\(\[]?(?:at\s+)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[\)\]]?\b', chunk["text"])
        
        # Also look for the format where "at" replaces the @ symbol
        at_emails = re.findall(r'([a-zA-Z0-9._%+-]+)\s+(?:\(at\)|at)\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', chunk["text"])
        for username, domain in at_emails:
            emails.append(f"{username}@{domain}")
            
        chunk["emails"] = emails

    return chunks