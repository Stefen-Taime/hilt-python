# hilt/converters/csv.py
"""Utilities for converting HILT JSONL event logs into CSV files."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from hilt.io.session import Session


DEFAULT_COLUMNS: List[str] = [
    "event_id",
    "timestamp",
    "session_id",
    "actor.type",
    "actor.id",
    "action",
]


def convert_to_csv(
    input_file: str,
    output_file: str,
    columns: Optional[List[str]] = None,
    readable: bool = True,
    include_metadata: bool = False
) -> None:
    """Convert a JSONL file of HILT events into a CSV file.

    Args:
        input_file: Path to the source JSONL file.
        output_file: Path where the CSV data should be written.
        columns: Optional list of columns (only for readable=False).
        readable: If True, create a human-readable CSV (default).
        include_metadata: If True and readable=True, include detailed metadata.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If a line in the JSONL file contains invalid JSON.
    """
    resolved_input = Path(input_file)
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Mode lisible (nouveau comportement par défaut)
    if readable:
        _convert_to_readable_csv(input_file, output_file, include_metadata)
        return
    
    # Mode legacy (ancien comportement)
    _convert_to_flat_csv(input_file, output_file, columns)


def _format_timestamp(timestamp: Any) -> str:
    """Formater un timestamp en string lisible.
    
    Args:
        timestamp: datetime object ou string ISO
        
    Returns:
        String formatée "YYYY-MM-DD HH:MM:SS"
    """
    if isinstance(timestamp, str):
        # Si c'est déjà une string, essayer de la parser
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            # Si ça échoue, extraire date/heure manuellement
            if 'T' in timestamp:
                date_part = timestamp.split('T')[0]
                time_part = timestamp.split('T')[1][:8]
                return f"{date_part} {time_part}"
            return timestamp
    else:
        # Si c'est un objet datetime
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _convert_to_readable_csv(
    input_file: str,
    output_file: str,
    include_metadata: bool
) -> None:
    """Convertir en CSV lisible."""
    
    # Colonnes selon le mode
    if include_metadata:
        fieldnames = [
            "timestamp",
            "session_id",
            "actor",
            "action",
            "message",
            "retrieved_docs",
            "client_name",
            "continent",
            "product",
            "quantity",
            "tokens_used"
        ]
    else:
        fieldnames = [
            "timestamp",
            "session",
            "speaker",
            "action",
            "message"
        ]
    
    rows = []
    
    # Lire les events
    with Session(input_file, mode="r") as session:
        for event in session.read():
            if include_metadata:
                row = _extract_detailed_row(event)
            else:
                row = _extract_simple_row(event)
            rows.append(row)
    
    # Écrire le CSV
    resolved_output = Path(output_file)
    with resolved_output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _extract_simple_row(event) -> Dict[str, Any]:
    """Extraire une ligne simple et lisible."""
    
    # Formater l'acteur
    if event.actor.type == "human":
        speaker = f"👤 {event.actor.id}"
    elif event.actor.type == "agent":
        speaker = f"🤖 {event.actor.id}"
    elif event.actor.type == "tool":
        speaker = f"🔍 {event.actor.id}"
    else:
        speaker = f"{event.actor.type}: {event.actor.id}"
    
    # Nettoyer et normaliser le texte
    text = event.content.text
    
    # Remplacer les retours à la ligne par des espaces
    text = text.replace('\n', ' ')
    
    # Remplacer les espaces multiples par un seul espace
    import re
    text = re.sub(r'\s+', ' ', text)
    
    # Nettoyer les caractères markdown si souhaité
    # text = text.replace('- ', '').replace('* ', '').replace('  ', ' ')
    
    # Enlever les espaces en début/fin
    text = text.strip()
    
    # Raccourcir le texte si trop long
    if len(text) > 150:
        text = text[:147] + "..."
    
    return {
        "timestamp": _format_timestamp(event.timestamp),
        "session": event.session_id.replace("rag_chat_", "Conv.").replace("openai_", ""),
        "speaker": speaker,
        "action": event.action,
        "message": text
    }


def _extract_detailed_row(event) -> Dict[str, Any]:
    """Extraire une ligne avec toutes les métadonnées."""
    
    row = {
        "timestamp": _format_timestamp(event.timestamp),
        "session_id": event.session_id,
        "actor": f"{event.actor.type}/{event.actor.id}",
        "action": event.action,
        "message": event.content.text,
        "retrieved_docs": "",
        "client_name": "",
        "continent": "",
        "product": "",
        "quantity": "",
        "tokens_used": ""
    }
    
    # Pour les completions : nombre de docs récupérés
    if event.action == "completion" and event.extensions:
        retrieved_ids = event.extensions.get("retrieved_ids", [])
        if retrieved_ids:
            row["retrieved_docs"] = len(retrieved_ids)
    
    # Pour les retrievals : info du document
    if event.action == "retrieval" and event.provenance:
        retrieval = event.provenance.get("retrieval", {})
        row["client_name"] = retrieval.get("client_name", "")
        row["continent"] = retrieval.get("continent", "")
        row["product"] = retrieval.get("product", "")
        row["quantity"] = retrieval.get("quantity", "")
    
    # Tokens
    if event.metrics and event.metrics.tokens:
        row["tokens_used"] = event.metrics.tokens.get("total", "")
    
    return row


def _convert_to_flat_csv(
    input_file: str,
    output_file: str,
    columns: Optional[List[str]]
) -> None:
    """Convertir en CSV aplati (ancien comportement, legacy)."""
    resolved_input = Path(input_file)
    resolved_output = Path(output_file)
    
    fieldnames = list(columns) if columns is not None else list(DEFAULT_COLUMNS)
    rows: List[Dict[str, Any]] = []

    with resolved_input.open("r", encoding="utf-8") as source:
        for index, raw_line in enumerate(source, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {index}: {error.msg}") from error
            flattened = _flatten_event(event)
            rows.append(flattened)
            if columns is None:
                _extend_fieldnames(fieldnames, flattened.keys())

    with resolved_output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row_data in rows:
            writer.writerow({field: _normalize_value(row_data.get(field)) for field in fieldnames})


def _flatten_event(event: Any) -> Dict[str, Any]:
    """Flatten an event object into a dictionary with dot-separated keys."""
    if not isinstance(event, dict):
        raise ValueError("Each JSONL line must represent a JSON object.")
    flattened: Dict[str, Any] = {}
    _flatten_into(event, flattened)
    return flattened


def _flatten_into(value: Any, accumulator: Dict[str, Any], parent_key: str | None = None) -> None:
    """Recursively flatten a nested value into dot-notation keys."""
    if isinstance(value, dict):
        for key, child in value.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            _flatten_into(child, accumulator, new_key)
        return

    if isinstance(value, list):
        if parent_key is None:
            raise ValueError("Encountered a top-level list which cannot be flattened.")
        accumulator[parent_key] = _serialize_list(value)
        return

    if parent_key is None:
        raise ValueError("Encountered a top-level scalar which cannot be flattened.")

    accumulator[parent_key] = value


def _serialize_list(items: Iterable[Any]) -> str:
    """Serialize a list into either a semicolon-separated string or JSON."""
    items = list(items)
    if _is_simple_list(items):
        return ";".join("" if item is None else str(item) for item in items)
    return json.dumps(items, ensure_ascii=False)


def _is_simple_list(items: List[Any]) -> bool:
    """Return True if the list only contains simple scalar values."""
    simple_types = (str, int, float, bool, type(None))
    return all(isinstance(item, simple_types) for item in items)


def _extend_fieldnames(fieldnames: List[str], candidates: Iterable[str]) -> None:
    """Extend the CSV header with new fieldnames while preserving order."""
    for candidate in candidates:
        if candidate not in fieldnames:
            fieldnames.append(candidate)


def _normalize_value(value: Any) -> str:
    """Normalize values for CSV output, replacing None with an empty string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)