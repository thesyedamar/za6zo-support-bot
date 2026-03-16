# test_bot.py

from bot.rag_chain import ask_zabot

test_questions = [
    # English
    "What is Za6zo?",
    # Roman Urdu
    "Za6zo mein driver kaise bante hain?",
    # Roman Pashto
    "Za6zo tsanga sawa kawam?",
    # Roman Pashto
    "Driver kawam ghwaram, tsanga register kawam?",
    # Urdu script
    "زا سکسو کې سواری کولو لپاره دا اپ سم دی؟",
    # Roman Urdu
    "City to city ride available hai?",
    # Roman Pashto
    "Da Za6zo qemat tsanga da?",
]

print("🤖 ZaBot — Trilingual Test\n" + "="*45)
for q in test_questions:
    print(f"\n👤 User: {q}")
    answer = ask_zabot(q)
    print(f"🤖 ZaBot: {answer}")
    print("-"*45)