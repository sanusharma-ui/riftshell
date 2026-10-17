"""Offline query routing, independent of command names and argument binding.

These contrasting examples describe kinds of requests, not phrase/keyword rules.
MiniLM embeds the entire request; weak or conflicting evidence abstains. This
router can choose a smaller prompt, but can never authorize an action.
"""
from dataclasses import dataclass
from functools import lru_cache
from threading import RLock

from ai.intent_model import local_encoder
from ai.semantic_catalog import SEMANTIC_INTENTS


QUERY_EXAMPLES = {
    "conversation": (
        "Hello, how are you doing?", "Thank you for your help",
        "Who are you and what can you help me with?",
        "Who was Albert Einstein?", "Tell me about the history of India",
        "What is the capital of France?", "Why does the sky look blue?",
        "How does gravity work?", "Explain photosynthesis in simple terms",
        "What is machine learning?", "Explain dependency injection",
        "Explain the difference between a process and a thread",
        "How does a computer store files?", "What is a directory?",
        "Explain what the delete command does", "How do I list files in a terminal?",
        "What is the difference between Git merge and rebase?",
        "Explain the purpose of git status", "What do shell commands mean?",
        "How can I remove files safely?", "What does an IP address mean?",
        "Teach me Python with examples", "Show an example of recursion in chat",
        "Write a poem about the ocean", "Tell me a funny story",
        "Help me plan how to learn programming", "Give me ideas for a science project",
        "What are the advantages of renewable energy?",
        "Explain this concept in more detail", "Give another example of that idea",
        "What does that word mean?", "Translate this sentence into English",
        "Rewrite this paragraph more clearly", "Summarize the following text",
        "What is a healthy way to organize my study time?",
        "Why do people dream?", "How can I improve my communication skills?",
        "What is the weather forecast?", "Who won the latest cricket match?",
        "Tum kaise ho?", "Mujhe artificial intelligence ke baare mein batao",
        "Recursion kya hota hai?", "Computer kaise kaam karta hai?",
    ),
    "workspace": (
        "List files", "Show folders", "Show the files and folders in this directory",
        "Which subdirectories exist here?", "Where am I in the terminal?",
        "Go to the source folder", "Create an empty file called notes.txt",
        "Create a directory named reports", "Copy notes.txt to backup.txt",
        "Rename the file", "Delete the old log files", "Move these folders",
        "Open this document", "Show the contents of README.md",
        "Read main.py and explain how it works", "Explain this project",
        "Summarize this repository", "Check the files in my workspace",
        "Find the bug in my application", "Fix the code in app.py",
        "Write a calculator in calculator.py", "Build a website in this project",
        "Run the tests", "Execute this command in the terminal",
        "Show running processes", "Check this computer's memory usage",
        "Show my network configuration", "Check available disk space",
        "Display the current time and date", "Show installed plugins",
        "Show the version of this application", "List available shell commands",
        "Change the terminal theme", "Clear this terminal", "Close the shell",
        "Compute this expression", "Encode this string as base64",
        "Hash this file", "Download this URL", "Unzip this archive",
        "Sort the output", "Set an environment variable", "Create a command alias",
        "Show Git changes", "Commit the staged files", "Push the branch",
        "List files and then check Git status", "Capture a screenshot",
        "Mujhe saare folders dikhao", "src mein jao", "File delete karo",
        "Is project ko samjhao", "app.py mein code likho",
    ),
    # Context-sensitive requests retain the planner and its evidence. In
    # particular, an explanation of actual output is not a general fact query.
    "context": (
        "Do it", "Yes, proceed", "Continue with that task", "Try again",
        "Use the other one", "Do the same for this file", "Undo that change",
        "What happened?", "Did it work?", "Why did that fail?",
        "Explain the last command output", "What does this terminal error mean?",
        "Analyze the previous result", "What should I do next with this project?",
        "Do not delete that file", "Should I remove this file?",
    ),
}
_INDEX_LOCK = RLock()


@dataclass(frozen=True)
class QueryIntent:
    kind: str = "uncertain"
    score: float = 0.0
    margin: float = 0.0


@lru_cache(maxsize=1)
def _query_index():
    encoder = local_encoder()
    if encoder is None:
        return None
    with _INDEX_LOCK:
        texts = [text for examples in QUERY_EXAMPLES.values() for text in examples]
        owners = [kind for kind, examples in QUERY_EXAMPLES.items() for _ in examples]
        # Capability descriptions are semantic task evidence only; no command
        # names, regex matching, slot binding or executable candidates here.
        capabilities = [text for item in SEMANTIC_INTENTS for text in item.examples]
        texts.extend(capabilities)
        owners.extend(["workspace"] * len(capabilities))
        vectors = encoder.np.concatenate([
            encoder.encode(texts[i:i + 16]) for i in range(0, len(texts), 16)
        ])
        return encoder, vectors, owners


def classify_query(text: str) -> QueryIntent:
    # Never classify only a prefix: trailing constraints change the intent.
    if not text.strip() or len(text) > 2048:
        return QueryIntent()
    try:
        index = _query_index()
        if index is None:
            return QueryIntent()
        encoder, vectors, owners = index
        values = encoder.encode([text])[0] @ vectors.T
        if not encoder.np.isfinite(values).all():
            return QueryIntent()
        scores = sorted(
            ((max(float(v) for v, owner in zip(values, owners) if owner == kind), kind)
             for kind in QUERY_EXAMPLES), reverse=True,
        )
        score, kind = scores[0]
        margin = score - scores[1][0]
        # Topic similarity alone (e.g. a general question about memory) must
        # not select the expensive workspace prompt. Be stricter for tasks.
        minimum = .64 if kind == "workspace" else .48 if kind == "context" else .30
        if score < minimum or margin < .08:
            kind = "uncertain"
        return QueryIntent(kind, score, margin)
    except Exception:
        # An optional model failure must leave the original action path usable.
        return QueryIntent()
