"""Auto-instrumentation for HILT - Zero friction LLM observability."""

from typing import Optional, List, Dict, Union
from pathlib import Path

from hilt.io.session import Session
from hilt.instrumentation.context import get_context
from hilt.instrumentation.openai_instrumentor import instrument_openai, uninstrument_openai


def instrument(
    # Backend selection
    backend: Optional[str] = None,
    # Local backend
    filepath: Optional[Union[str, Path]] = None,
    # Google Sheets backend
    sheet_id: Optional[str] = None,
    credentials_path: Optional[str] = None,
    credentials_json: Optional[Dict] = None,
    worksheet_name: str = "Logs",
    columns: Optional[List[str]] = None,
    # Providers to instrument
    providers: Optional[List[str]] = None,
) -> Session:
    """
    🚀 Enable automatic LLM observability with HILT.
    
    After calling this function once, all OpenAI chat completion calls are
    automatically logged without any code changes.
    
    Args:
        backend: Backend type - "local" (JSONL) or "sheets" (Google Sheets)
        
        Local backend:
            filepath: Path to .jsonl file (e.g., "logs/chat.jsonl")
        
        Google Sheets backend:
            sheet_id: Google Sheet ID from URL
            credentials_path: Path to service account credentials JSON
            credentials_json: Credentials as dict (alternative to file)
            worksheet_name: Worksheet name (default: "Logs")
            columns: List of columns to display (default: all 14 columns)
        
        providers: List of providers to instrument (default: ["openai"])
            Options: "openai"
    
    Returns:
        Session object (can be used with context manager if needed)
    
    Examples:
        >>> # Option 1: Local JSONL file
        >>> from hilt import instrument
        >>> instrument(backend="local", filepath="logs/chat.jsonl")
        >>> 
        >>> # Your existing code works unchanged!
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> response = client.chat.completions.create(
        ...     model="gpt-4o-mini",
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
        >>> # ✅ Automatically logged to logs/chat.jsonl
        
        >>> # Option 2: Google Sheets (real-time collaboration)
        >>> instrument(
        ...     backend="sheets",
        ...     sheet_id="1abc-xyz",
        ...     credentials_path="credentials.json"
        ... )
        >>> # ✅ All LLM calls logged to Google Sheets in real-time
        
        >>> # Option 3: Custom columns in Sheets
        >>> instrument(
        ...     backend="sheets",
        ...     sheet_id="1abc-xyz",
        ...     columns=['timestamp', 'message', 'cost_usd', 'status_code']
        ... )
    
    Notes:
        - Call once at app startup
        - Thread-safe (works with FastAPI, Flask, etc.)
        - Zero performance overhead when not logging
        - Use uninstrument() to disable
    """
    
    # Validate backend
    if backend is None:
        if filepath:
            backend = "local"
        elif sheet_id:
            backend = "sheets"
        else:
            raise ValueError(
                "Must specify either backend='local' with filepath "
                "or backend='sheets' with sheet_id"
            )
    
    # Default providers
    if providers is None:
        providers = ["openai"]
    
    # Create session based on backend
    if backend == "local":
        if filepath is None:
            filepath = "logs/hilt.jsonl"
        
        session = Session(
            backend="local",
            filepath=filepath,
            mode="a",
            create_dirs=True
        )
        print(f"✅ HILT instrumentation enabled")
        print(f"   Backend: Local JSONL")
        print(f"   File: {filepath}")
    
    elif backend == "sheets":
        session = Session(
            backend="sheets",
            sheet_id=sheet_id,
            credentials_path=credentials_path,
            credentials_json=credentials_json,
            worksheet_name=worksheet_name,
            columns=columns
        )
        print(f"✅ HILT instrumentation enabled")
        print(f"   Backend: Google Sheets")
        print(f"   Sheet ID: {sheet_id}")
        print(f"   Worksheet: {worksheet_name}")
    
    else:
        raise ValueError(f"Invalid backend: {backend}. Must be 'local' or 'sheets'")
    
    # Open session (it will stay open for the app lifetime)
    session.open()
    
    # Set global session in context
    context = get_context()
    context.set_global_session(session)
    
    # Instrument providers
    print(f"   Providers: {', '.join(providers)}")
    
    if "openai" in providers:
        instrument_openai()
    
    return session


def uninstrument():
    """
    Disable HILT instrumentation.
    
    Removes all monkey-patching and closes the session.
    
    Example:
        >>> from hilt import uninstrument
        >>> uninstrument()
        >>> # LLM calls are no longer logged
    """
    context = get_context()
    
    # Close session if exists
    if context.session:
        try:
            context.session.close()
        except:
            pass
    
    # Clear context
    context.clear()
    
    # Uninstrument providers
    uninstrument_openai()
    
    print("🔓 HILT instrumentation disabled")


__all__ = ['instrument', 'uninstrument']
