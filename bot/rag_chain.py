# bot/rag_chain.py — with reliable code-level language detection

import os
import re
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from bot.prompts import SYSTEM_PROMPT

load_dotenv()

CHROMA_DB_DIR = "chroma_db"

# --- Per-session chat history ---
session_histories: dict = {}

def get_history(session_id: str) -> list:
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_histories[session_id]


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# -----------------------------------------------------------
# LANGUAGE DETECTOR — pure Python, no extra libraries needed
# Checks for script type and keyword signals
# -----------------------------------------------------------
def detect_language(text: str) -> str:
    """
    Returns one of: 'urdu_script', 'pashto_script',
                    'roman_pashto', 'roman_urdu', 'english'
    """
    # 1. Urdu/Pashto script detection (Arabic script characters)
    arabic_script = re.findall(r'[\u0600-\u06FF\u0750-\u077F]', text)
    if arabic_script:
        # Pashto-specific letters not in standard Urdu
        pashto_specific = re.findall(r'[ټګځڅچډړږښڼۍې]', text)
        if pashto_specific:
            return 'pashto_script'
        return 'urdu_script'

    text_lower = text.lower()

    # 2. Roman Pashto keyword signals
    # These words are distinctly Pashto and rarely appear in Urdu
    pashto_signals = [
        'kawam', 'kawai', 'kawel', 'sawa', 'wror', 'khwara',
        'tsanga', 'manana', 'kala yast', 'cherta yast', 'yam',
        'ghwaram', 'ghwari', 'da ride', 'da za6zo', 'sta',
        'zma', ' aw ', 'che ', ' ke ', ' de ', ' pa ',
        'driver yam', 'sawa kawa', 'qemat', 'kana', 'raka',
        'wokra', 'dey', ' da ', 'larai', 'nishta', 'kha wror',
        'kha khwara', 'register kawam', 'app download kawa'
    ]
    pashto_count = sum(1 for signal in pashto_signals if signal in text_lower)

    # 3. Roman Urdu keyword signals
    urdu_signals = [
        ' hai', ' hain', ' kar ', ' mein ', ' aap ', ' kya ',
        ' kaise', ' nahi', ' hoga', ' wala', ' ko ', ' se ',
        ' ka ', ' ki ', ' ke ', 'karein', 'chahiye', 'poochna',
        'batayein', 'kijiye', 'shukriya', 'meherbani', 'janab',
        'bhai', 'apna', 'hamara', 'tumhara', 'booking', 'ride karni'
    ]
    urdu_count = sum(1 for signal in urdu_signals if signal in text_lower)

    # 4. Decision logic
    if pashto_count >= 2:
        return 'roman_pashto'
    if pashto_count == 1 and urdu_count == 0:
        return 'roman_pashto'
    if urdu_count >= 1:
        return 'roman_urdu'
    if pashto_count == 1 and urdu_count >= 1:
        return 'roman_urdu'  # mixed, default to urdu

    # 5. Fallback: if mostly non-English words, guess roman_urdu
    english_words = set(['the','is','are','was','were','how','what',
                         'where','when','why','can','do','does','have',
                         'has','will','would','should','could','i','my',
                         'you','your','please','help','need','want','get'])
    words = set(text_lower.split())
    english_count = len(words & english_words)
    if english_count >= 2:
        return 'english'

    return 'roman_urdu'  # safe default for Pakistani users


def get_language_instruction(lang: str) -> str:
    """
    Returns an explicit instruction injected into the prompt
    telling Gemini exactly what language to reply in.
    """
    instructions = {
        'english': (
            "IMPORTANT: The user wrote in ENGLISH. "
            "You MUST reply in English only. Do not use Urdu or Pashto."
        ),
        'urdu_script': (
            "IMPORTANT: The user wrote in Urdu script. "
            "You MUST reply in Urdu script (not Roman Urdu, actual Urdu text). "
            "Do not reply in English or Pashto."
        ),
        'pashto_script': (
            "IMPORTANT: The user wrote in Pashto script. "
            "You MUST reply in Pashto script. "
            "Do not reply in English or Urdu."
        ),
        'roman_pashto': (
            "IMPORTANT: The user wrote in Roman Pashto. "
            "You MUST reply in Roman Pashto (Pashto words written in English letters). "
            "Use words like: kha, manana, wror, kawai, da, sawa, tsanga, ghwaram, etc. "
            "Do NOT reply in English or Urdu. Reply in Roman Pashto only."
        ),
        'roman_urdu': (
            "IMPORTANT: The user wrote in Roman Urdu (Urdu words in English letters). "
            "You MUST reply in Roman Urdu. "
            "Use words like: hai, hain, aap, kar, mein, zaroor, etc. "
            "Do NOT reply in English or Pashto. Reply in Roman Urdu only."
        ),
    }
    return instructions.get(lang, instructions['roman_urdu'])


# --- Build components once at startup ---
_retriever = None
_llm = None

def _build_components():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    vectorstore = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3,
        convert_system_message_to_human=True
    )
    return retriever, llm

def _get_components():
    global _retriever, _llm
    if _retriever is None:
        print("🔄 Building RAG components...")
        _retriever, _llm = _build_components()
        print("✅ RAG components ready")
    return _retriever, _llm


# --- Main function ---
def ask_zabot(user_message: str, session_id: str = "default") -> str:
    retriever, llm = _get_components()
    history = get_history(session_id)

    # STEP 1: Detect language from user message
    detected_lang = detect_language(user_message)
    lang_instruction = get_language_instruction(detected_lang)
    print(f"🌐 Detected language: {detected_lang}")

    try:
        # STEP 2: Retrieve relevant Za6zo knowledge
        docs = retriever.invoke(user_message)
        context = format_docs(docs)

        # STEP 3: Build prompt — language instruction goes LAST
        # so it's the freshest thing in Gemini's context window
        messages = [
            ("system",
             SYSTEM_PROMPT
             + f"\n\nZa6zo knowledge base context:\n{context}"
             + f"\n\n{lang_instruction}"   # ← explicit language override
            )
        ]

        # STEP 4: Add last 5 exchanges from history
        for msg in history[-10:]:
            messages.append(msg)

        # STEP 5: Add current user message
        messages.append(("human", user_message))

        # STEP 6: Call Gemini
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({})

        # STEP 7: Save to history
        history.append(("human", user_message))
        history.append(("assistant", answer))

        return answer

    except Exception as e:
        print(f"❌ ZaBot error: {e}")
        # Fallback in all three languages
        return (
            "Maafi chahta hoon, abhi kuch technical masla aa gaya hai.\n"
            "Sorry, a technical issue occurred. Please try again.\n"
            "Bakhana ghwaram, technical stونزه رامنځته شوه. بيا هڅه وکړئ."
        )