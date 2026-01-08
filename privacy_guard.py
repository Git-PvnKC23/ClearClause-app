"""
Privacy Guard Module for ClearClause
Handles PII detection and redaction using spaCy
"""

import spacy
import re
import subprocess
import sys
from typing import Dict, Tuple, List

# Entity types to redact
REDACTABLE_ENTITIES = {"PERSON", "ORG", "DATE", "GPE"}


def _load_spacy_model():
    """
    Loads spaCy model safely with fallback logic.
    Attempts to load en_core_web_sm, and if not found, 
    tries to download it dynamically.
    
    Returns:
        spacy.Language: Loaded spaCy model
        
    Raises:
        RuntimeError: If model cannot be loaded or downloaded
    """
    model_name = "en_core_web_sm"
    
    # Try to load the model
    try:
        nlp = spacy.load(model_name)
        return nlp
    except OSError:
        pass
    
    # Model not found, attempt to download it
    print(f"Model '{model_name}' not found. Attempting to download...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "spacy", "download", model_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Try loading again after download
        nlp = spacy.load(model_name)
        print(f"✅ Successfully downloaded and loaded '{model_name}'")
        return nlp
    except Exception as e:
        raise RuntimeError(
            f"Failed to load or download spaCy model '{model_name}'. "
            f"Error: {str(e)} "
            f"Please manually install using: python -m spacy download en_core_web_sm"
        )


# Initialize spaCy model
try:
    nlp = _load_spacy_model()
except RuntimeError as e:
    raise RuntimeError(str(e))


def redact_pii(text: str) -> str:
    """
    Redacts Personally Identifiable Information (PII) from text using spaCy.
    
    Detects and redacts:
    - PERSON: People names
    - ORG: Organizations
    - DATE: Dates
    - GPE: Geopolitical entities (countries, cities)
    - PHONE_NUMBER: Phone numbers (using pattern matching)
    
    Args:
        text (str): The input text to redact
        
    Returns:
        str: Text with PII replaced with [REDACTED]
    """
    if not text or not isinstance(text, str):
        return text
    
    # Process text with spaCy
    doc = nlp(text)
    
    # Track character positions to redact (as tuples of start, end)
    redactions: List[Tuple[int, int]] = []
    
    # Find spaCy entities to redact
    for ent in doc.ents:
        if ent.label_ in REDACTABLE_ENTITIES:
            redactions.append((ent.start_char, ent.end_char))
    
    # Detect phone numbers using regex pattern
    # Matches formats like: (123) 456-7890, 123-456-7890, 123.456.7890, +1 123 456 7890
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    
    for match in re.finditer(phone_pattern, text):
        redactions.append((match.start(), match.end()))
    
    # Remove duplicates and sort in reverse order to maintain string indices
    redactions = sorted(set(redactions), reverse=True)
    
    # Apply redactions from end to start (to preserve character positions)
    redacted_text = text
    for start, end in redactions:
        redacted_text = redacted_text[:start] + "[REDACTED]" + redacted_text[end:]
    
    return redacted_text


def get_redaction_summary(original_text: str, redacted_text: str) -> Dict:
    """
    Generates a comprehensive summary of redactions made.
    
    Args:
        original_text (str): Original text before redaction
        redacted_text (str): Text after redaction
        
    Returns:
        dict: Summary containing:
            - total_redactions: Count of [REDACTED] markers
            - entity_breakdown: Dict with counts of each entity type
            Example: {
                'total_redactions': 5,
                'entity_breakdown': {'PERSON': 2, 'ORG': 1, 'DATE': 1, 'PHONE': 1}
            }
    """
    if not original_text or not isinstance(original_text, str):
        return {
            "total_redactions": 0,
            "entity_breakdown": {}
        }
    
    # Count total redactions
    redaction_count = len(re.findall(r'\[REDACTED\]', redacted_text))
    
    # Process original text with spaCy to get entity breakdown
    doc = nlp(original_text)
    entity_counts: Dict[str, int] = {}
    
    for ent in doc.ents:
        if ent.label_ in REDACTABLE_ENTITIES:
            label = ent.label_
            entity_counts[label] = entity_counts.get(label, 0) + 1
    
    # Count phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    phone_count = len(re.findall(phone_pattern, original_text))
    if phone_count > 0:
        entity_counts["PHONE"] = phone_count
    
    return {
        "total_redactions": redaction_count,
        "entity_breakdown": entity_counts
    }


def get_entity_details(text: str) -> Dict:
    """
    Gets detailed information about detected entities.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Detailed entity information with text and labels
        Example: {
            'entities': [
                {'text': 'John Doe', 'label': 'PERSON', 'start': 0, 'end': 8},
                ...
            ],
            'total_entities': 1
        }
    """
    if not text or not isinstance(text, str):
        return {"entities": [], "total_entities": 0}
    
    doc = nlp(text)
    entities = []
    
    for ent in doc.ents:
        if ent.label_ in REDACTABLE_ENTITIES:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
    
    # Add phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    for match in re.finditer(phone_pattern, text):
        entities.append({
            "text": match.group(0),
            "label": "PHONE",
            "start": match.start(),
            "end": match.end()
        })
    
    return {
        "entities": entities,
        "total_entities": len(entities)
    }

