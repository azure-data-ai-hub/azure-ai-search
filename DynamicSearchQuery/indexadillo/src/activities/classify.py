from application.app import app
from typing import List, Dict
import logging
import os
from openai import AzureOpenAI

logger = logging.getLogger("scripts")

@app.function_name(name="classify")
@app.activity_trigger(input_name="chunks")
def classifychunks(chunks: List[Dict]) -> List[Dict]:
    logger.info("classify the chunks")
    logger.info(f"Number of chunks: {len(chunks)}")

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AOPENAI_ENDPOINT"),
        api_key=os.getenv("AOPENAI_API_KEY"),
        api_version=os.getenv("AOPENAI_API_VERSION")
    )

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        prompt = f"""
        Classify the following text into exactly one category (no explanation):
        PreambleBlock, TermsandconditionsBlock, SignatureBlock,
        ServiceBlock, PricingBlock, Other.  

        You Must do:
        1. Only return the classification (no explanation).
        2. Classification must be strictly one of:
           PreambleBlock, TermsandconditionsBlock,
           SignatureBlock, ServiceBlock, PricingBlock, Other.
        3. Refer Examples in the prompt to better understand the context.
        4. Do not use any other classification or explanation.

        Classification guidelines:
        PreambleBlock: introductory or background statements
        TermsandconditionsBlock: references terms, conditions, obligations, disclaimers, or policies
        SignatureBlock: references signature lines or signatories
        ServiceBlock: references scope of services or the services provided
        PricingBlock: references fees, costs, or pricing details
        Other: if no clear match above

        Example#1:
        Text: This Agreement contains the entire agreement between the parties with respectto the subject matter hereof and supersedes all oral understandings, representations, prior discussions andpreliminary agreements. Any representations, warranties, promise or conditions not expressly contained in thisAgreement shall not be binding upon the parties.MICROSOFT CORPORATIONBy1281.NameRex SmithTitleEM MIN OPSSignature Date6-29-00 XXXCompany, INC.ByNameAAAPersonTitleBBBTitleSignature Date6/29/00US 6/29/0FINANCEAPPROVALAPPROVED26/29/09EXODUS
        Classification: SignatureBlock

        Example#2:
        Text: 13.TERM & TERMINATION.(a)Duration. This Agreement shall commence as of the Effective Date and shall continue in effectuntil terminated in accordance with this Section 13, provided that XXXCompany must complete all Services described inany then-effective Schedule which has not been previously terminated. YYYCompany may elect to terminate thisAgreement (and/or any Schedule) term without cause or without the occurrence of a Default, which terminationshall be effective upon ninety (90) days written notice of such cancellation. Except in cases of cancellation forDefault as specified in Section 13(b) of this Agreement, Microsoft will pay for all Services performed by Exodusuntil the date of termination of the Agreement (and/or applicable Schedule).(b)Early Termination and Default. The term of this Agreement is subject to early termination ofthe Agreement in accordance with the following:(1)This Agreement (and/or any Schedule) shall terminate automatically upon a Defaultunder Section 13(b)(ii)(D) below. Either party shall have the right to terminate this Agreement (and/or anySchedule) immediately upon a Default under Section 13(b)(ii)(A) or (B)
        Classification: TermsandconditionsBlock

        Example#3:
        Text: The term of the Services provided under this Schedule shall commence on July 1,2000 and shall expire on theone year anniversary of such date. The parties may renew the Term of this Schedule upon mutual writtenagreement
        Classification: TermsandconditionsBlock

        Example#4:
        Text: MASTER SERVICES AGREEMENTCONFIDENTIALThis Master Services Agreement ("Agreement") is made as of June 29, 2000 (the "Effective Date") by andbetween YYYCompany, a Washington corporation, with its chief executive offices at and amailing address of One Redmond, WA 98052 ("YYYCompany"), and XXXCompany, Inc. a ZZZ State corporation, with a mailing address of, and its chief executive offices at SantaClara, CA 95054 ("XXXCompany")
        Classification: PreambleBlock
        
        Text: {text}
                """.strip()

        response = client.chat.completions.create(
            model=os.getenv("AOPENAI_MODEL_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "You are an expert legal contract documents analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0
        )

        classification = response.choices[0].message.content.strip()
        chunk["classification"] = classification

        logger.info(f"Chunk {i}, Text: {text}, classification: {classification}")

    return chunks