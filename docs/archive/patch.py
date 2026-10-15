import re

with open('backend/app/services/document_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update JobSteps
content = content.replace('JobStep.EXTRACT', 'JobStep.EXTRACTION')
content = content.replace('JobStep.CHUNK', 'JobStep.CHUNKING')
content = content.replace('JobStep.EMBED', 'JobStep.EMBEDDING')
content = content.replace('JobStep.KG_INDEX', 'JobStep.KG_INDEXING')
content = content.replace('JobStep.COMPLETE', 'JobStep.COMPLETED')
content = content.replace('document.status.CHUNKING', 'DocumentStatus.CHUNKING')
content = content.replace('document.status.EMBEDDING', 'DocumentStatus.EMBEDDING')
content = content.replace('document.status.INDEXING_KG', 'DocumentStatus.INDEXING_KG')

with open('backend/app/services/document_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
