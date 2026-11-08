"""Trace the planning route for 'where we are right now'."""
import sys
sys.path.insert(0, '.')

from ai.query_intent import classify_query, QUERY_EXAMPLES
from ai.intent_model import local_encoder
from core.shell import Shell

enc = local_encoder()
print("Encoder:", enc)

shell = Shell()
names = shell.registry.all_names()
print("'where' in names:", 'where' in names)
print("'where we are right now' in names:", 'where we are right now' in names)

test_phrases = [
    "where",
    "where we are right now",
    "where are we",
    "where we are",
    "where am i",
]

for phrase in test_phrases:
    route = classify_query(phrase)
    print(f"  classify_query({phrase!r}) => kind={route.kind!r}, score={route.score:.3f}, margin={route.margin:.3f}")
