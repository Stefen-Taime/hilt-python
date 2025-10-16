"""Interactive E-Commerce RAG Chatbot with HILT logging (NO MESSAGE CONTENT)"""

from pathlib import Path
import os
import csv
import re
from collections import Counter
from hilt import instrument, uninstrument
from hilt.core.event import Event
from hilt.instrumentation.context import get_context
from openai import OpenAI

# Configuration
CSV_FILE = "products_knowledge.csv"
LOG_FILE = "logs/ecommerce_chat_no_msg.jsonl"

# Pour Google Sheets : décommentez et configurez
USE_SHEETS = False  # Changez en True pour utiliser Google Sheets
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
REPO_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(REPO_ROOT / "credentials.json")
)
# Check API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY missing")
    exit(1)

# Enable HILT logging WITHOUT message content
# Colonnes à logger (SANS le contenu des messages)
COLUMNS_NO_MESSAGE = [ 
    'timestamp',
    'conversation_id',
    'event_id',
    'reply_to',
    'status_code',
    'speaker',
    'action',
    # 'message',  ← EXCLU pour la confidentialité !
    'tokens_in',
    'tokens_out',
    'cost_usd',
    'latency_ms',
    'model'
]

if USE_SHEETS and SHEET_ID:
    # Option 1: Google Sheets avec colonnes personnalisées (SANS message)
    instrument(
        backend="sheets",
        sheet_id=SHEET_ID,
        credentials_path=CREDENTIALS_PATH,
        worksheet_name="E-Commerce Logs",
        columns=COLUMNS_NO_MESSAGE
    )
    print("✅ Logging to Google Sheets (message content excluded)")
else:
    # Option 2: Local JSONL avec colonnes filtrées (SANS message)
    instrument(
        backend="local",
        filepath=LOG_FILE,
        columns=COLUMNS_NO_MESSAGE
    )
    print("✅ Logging to local file (message content excluded)")
    print("📊 Only metadata logged, no message content")

def load_csv():
    """Load the knowledge base"""
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def tokenize(text):
    """Simple tokenization"""
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'can', 'it', 'this', 'that', 'these', 'those'}
    return [t for t in tokens if t not in stop_words and len(t) > 2]

def calculate_relevance_score(query, item):
    """Calculate relevance score using keyword matching"""
    query_tokens = tokenize(query)
    doc_text = f"{item['question']} {item['answer']} {item['category']}"
    doc_tokens = tokenize(doc_text)
    
    if not query_tokens or not doc_tokens:
        return 0.0
    
    doc_counter = Counter(doc_tokens)
    matches = sum(doc_counter[token] for token in query_tokens)
    base_score = matches / len(query_tokens)
    
    query_lower = query.lower()
    if query_lower in item['question'].lower():
        base_score += 0.5
    elif query_lower in item['answer'].lower():
        base_score += 0.3
    
    if any(token in item['category'].lower() for token in query_tokens):
        base_score += 0.2
    
    return min(base_score, 1.0)

def search_with_rag(query, kb, limit=3):
    """Advanced RAG search with scoring"""
    scored_items = []
    for item in kb:
        score = calculate_relevance_score(query, item)
        if score > 0:
            scored_items.append({
                'item': item,
                'score': score
            })
    
    scored_items.sort(key=lambda x: x['score'], reverse=True)
    return scored_items[:limit]

def log_retrieval_event(query, results, session_id):
    """Log RAG retrieval event to HILT (metadata only, no full text)"""
    session = get_context().session
    
    if not session:
        return
    
    # Prepare retrieval info
    sources = [
        {
            'id': r['item']['id'],
            'category': r['item']['category'],
            'score': round(r['score'], 3)
        }
        for r in results
    ]
    
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    
    # Log retrieval event with MINIMAL text (just metadata)
    session.append(Event(
        session_id=session_id,
        actor={"type": "system", "id": "rag"},
        action="retrieval",
        content={
            "text": f"Retrieved {len(results)} docs"  # ← Minimal text
        },
        extensions={
            "query_hash": hash(query) % 10000,  # Hash instead of full query
            "query_length": len(query),
            "num_results": len(results),
            "avg_relevance_score": round(avg_score, 3),
            "categories": list(set(r['item']['category'] for r in results)),
            "source_ids": [r['item']['id'] for r in results]
        }
    ))

def create_prompt(question, results):
    """Create the RAG prompt with sources"""
    if not results:
        return f"""You are a helpful shopping assistant. Answer the customer's question about our store.

Question: {question}

Answer professionally and helpfully."""
    
    ctx_parts = []
    for i, r in enumerate(results, 1):
        item = r['item']
        ctx_parts.append(
            f"[Info {i} - Category: {item['category']}]\n"
            f"Q: {item['question']}\n"
            f"A: {item['answer']}"
        )
    
    context = "\n\n".join(ctx_parts)
    
    return f"""You are a helpful shopping assistant for our online store. Use the following information to answer the customer's question accurately and professionally.

STORE INFORMATION:
{context}

CUSTOMER QUESTION: {question}

Provide a helpful, accurate answer. If the information is in the sources above, use it. If not, politely say you don't have that specific information and suggest contacting customer service."""

def display_sources(results):
    """Display retrieved sources"""
    if not results:
        print("   📭 No relevant information found")
        return
    
    print(f"   📚 Information found:")
    for i, r in enumerate(results, 1):
        item = r['item']
        score = r['score']
        bar = "█" * int(score * 10)
        emoji = {"electronics": "💻", "clothing": "👕", "home": "🏠", 
                 "shipping": "📦", "returns": "↩️", "payment": "💳",
                 "warranty": "🛡️", "account": "👤", "support": "💬",
                 "deals": "🏷️", "stock": "📊", "gift": "🎁", "reviews": "⭐"}.get(item['category'], "📝")
        print(f"      {i}. {emoji} [{item['category']}] {item['question'][:45]}...")
        print(f"         Relevance: {bar} {score:.2f}")

def chat():
    """Conversation loop with RAG"""
    kb = load_csv()
    client = OpenAI()
    session_id = "ecommerce_chat"
    
    print("🛍️  E-Commerce Shopping Assistant (RAG + HILT)")
    print("=" * 60)
    print(f"📚 {len(kb)} knowledge entries loaded")
    print(f"📊 Logs: {LOG_FILE if not USE_SHEETS else 'Google Sheets'}")
    print(f"🔒 Privacy: Message content NOT logged")
    print(f"🔍 AI-powered search enabled")
    print("\nCommands: 'quit' to exit, 'stats' for statistics")
    print("          'categories' to see all product categories\n")
    
    stats = {'queries': 0, 'total_tokens': 0, 'avg_relevance': []}
    categories = sorted(set(item['category'] for item in kb))
    
    while True:
        question = input("🛒 Customer: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if question.lower() == 'stats':
            print(f"\n📊 Session Statistics:")
            print(f"   Queries: {stats['queries']}")
            print(f"   Total tokens: {stats['total_tokens']:,}")
            if stats['avg_relevance']:
                avg = sum(stats['avg_relevance']) / len(stats['avg_relevance'])
                print(f"   Avg relevance: {avg:.3f}")
            print()
            continue
        
        if question.lower() == 'categories':
            print(f"\n📂 Available Categories:")
            emoji_map = {"electronics": "💻", "clothing": "👕", "home": "🏠", 
                        "shipping": "📦", "returns": "↩️", "payment": "💳",
                        "warranty": "🛡️", "account": "👤", "support": "💬",
                        "deals": "🏷️", "stock": "📊", "gift": "🎁", "reviews": "⭐"}
            for cat in categories:
                emoji = emoji_map.get(cat, "📝")
                count = sum(1 for item in kb if item['category'] == cat)
                print(f"   {emoji} {cat.capitalize()}: {count} entries")
            print()
            continue
        
        if not question:
            continue
        
        print()
        
        # 1. RAG Retrieval
        print("🔍 Searching knowledge base...")
        results = search_with_rag(question, kb, limit=3)
        
        # 2. Display sources
        display_sources(results)
        
        # 3. Log retrieval to HILT (metadata only)
        log_retrieval_event(question, results, session_id)
        
        # 4. Create prompt
        prompt = create_prompt(question, results)
        
        # 5. Call OpenAI (automatically logged by HILT)
        # Note: With column filtering, message won't be logged
        try:
            print("🤖 Assistant thinking...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional shopping assistant for an online store."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            print(f"\n🛍️  Assistant:")
            print(f"   {answer}\n")
            
            # Update stats
            stats['queries'] += 1
            stats['total_tokens'] += tokens
            if results:
                avg_score = sum(r['score'] for r in results) / len(results)
                stats['avg_relevance'].append(avg_score)
            
            # Show metrics
            print(f"📊 {tokens} tokens | {len(results)} sources", end="")
            if results:
                avg = sum(r['score'] for r in results) / len(results)
                print(f" | relevance: {avg:.2f}")
            else:
                print()
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    uninstrument()
    
    # Final stats
    print("\n" + "=" * 60)
    print("✅ Session Complete")
    print("=" * 60)
    print(f"📊 Total queries: {stats['queries']}")
    print(f"📊 Total tokens: {stats['total_tokens']:,}")
    if stats['avg_relevance']:
        overall_avg = sum(stats['avg_relevance']) / len(stats['avg_relevance'])
        print(f"📊 Overall avg relevance: {overall_avg:.3f}")
    
    if USE_SHEETS:
        print(f"💾 Logged to Google Sheets (no message content)")
    else:
        print(f"💾 Logged to: {LOG_FILE}")
        print(f"🔒 Message content excluded from logs")
    
    print()

if __name__ == "__main__":
    chat()