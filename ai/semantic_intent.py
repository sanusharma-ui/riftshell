"""Local learned intent ranking with independently validated literal arguments.

Similarity is evidence, not permission: request guards, complete slot layouts,
competing intents, registry membership and the normal safety policy all apply.
"""
from __future__ import annotations

import ast
from functools import lru_cache
import math
import re
from threading import RLock
from urllib.parse import urlsplit

from ai.command_intent import (
    CommandCandidate, Extraction, RuleIntentExtractor, _slot_value,
    normalize_request, quote_argument, valid_candidate,
)
from ai.intent_model import local_encoder
from ai.semantic_catalog import CHAT_EXAMPLES, SEMANTIC_INTENTS, SemanticIntent
from core.parser import CommandParser


ATOM = r'''(?:"[^"\r\n]+"|'[^'\r\n]+'|[^\s"']+)'''
QUOTED = re.compile(r'''"[^"\r\n]*"|(?<!\w)'[^'\r\n]*'(?!\w)''')
LITERAL = re.compile(r'''(?<!\w)(?:[A-Za-z]:[\\/][^\s]+|https?://[^\s]+|\S*[\\/]\S+|\S+\.[A-Za-z0-9]{1,8}\b|\d+(?:\.\d+)?)(?!\w)''')
BLOCK = re.compile(
    r"\b(?:no|not|never|dont|don't|cannot|can't|should|shouldn't|wouldn't|couldn't|"
    r"explain|describe|summarize|teach|meaning|means|example|examples|"
    r"if|unless|except|excluding|without|instead|but|then|also|otherwise|maybe|perhaps|"
    r"recursive|recursively|hidden|descending|ascending|largest|smallest|newest|oldest|"
    r"larger|smaller|older|newer|force|forcefully|overwrite|trash|recycle|"
    r"yesterday|tomorrow|pretend|imagine|said|says|asked|nahi|mat|another|somewhere|whichever|whatever)\b|"
    r"\b(?:how\s+(?:do|can|could|would|should|to)|why\b|what\s+(?:is|are)\s+(?:a|an)\b)",
    re.I,
)
REQUEST_START = re.compile(
    r"^(?:show|list|display|give|tell|let|what|which|where|how\s+(?:much|many|long)|"
    r"get|check|inspect|report|find|locate|search|look|view|see|print|echo|"
    r"go|navigate|switch|change|take|return|move|relocate|copy|duplicate|rename|"
    r"make|create|build|generate|delete|remove|erase|wipe|clear|close|exit|quit|"
    r"open|launch|start|stop|terminate|kill|run|execute|invoke|test|ping|"
    r"calculate|compute|evaluate|pick|choose|select|roll|wait|pause|sleep|"
    r"hash|encode|decode|convert|download|fetch|compress|zip|unzip|extract|unpack|package|"
    r"sort|order|filter|keep|omit|skip|drop|count|save|write|redisplay|"
    r"set|assign|unset|define|use|apply|stage|add|commit|pull|push|upload|bring)\b",
    re.I,
)
RESERVED_TARGETS = frozenset((
    "file files folder folders directory directories location contents subdirectories "
    "here there this that it them these those all everything anything something "
    "current working my your our me we us user computer system terminal console shell is are was were "
    "process processes running available installed please now today output result session repository tree diff "
    "branch branches theme themes another other somewhere somehow whatever whichever lives resides located "
    "in on at of from to for with the a an and or into as named called again first last "
    "not never code program app website script command commands"
).split())
TRAILER = r"(?:\s+(?:here|verbatim|alphabetically|seconds?|as\s+base64|to\s+base64|back\s+to\s+text|in\s+the\s+terminal|with\s+its\s+default\s+application|in\s+the\s+file\s+manager|in\s+Git|to\s+(?:the\s+)?Git\s+staging\s+area|from\s+disk|lines?\s+(?:of|from)\s+(?:the\s+)?(?:previous\s+output|piped\s+input)))?"
LEAD = r"(?P<lead>.+?)\s+"
SLOT0 = rf"(?P<s0>{ATOM})"
SLOT1 = rf"(?P<s1>{ATOM})"
LAYOUTS = {
    "one": re.compile(LEAD + SLOT0 + TRAILER, re.I),
    "location": re.compile(LEAD + r"(?:in|inside|under|of|on|for|at|from)\s+(?:the\s+)?(?:(?:folder|directory|drive)\s+)?" + SLOT0, re.I),
    "pair": re.compile(LEAD + SLOT0 + r"\s+(?:to|into|as|for)\s+(?:the\s+)?(?:(?:file|folder|directory|command|zip\s+archive)\s+)?" + SLOT1, re.I),
    "search": re.compile(LEAD + SLOT0 + r"\s+(?:in|inside|under)\s+(?:the\s+)?(?:(?:file|folder|directory)\s+)?" + SLOT1, re.I),
    "lines": re.compile(LEAD + r"(?P<s0>\d+)\s+lines?\s+(?:of|from|in)\s+(?:the\s+)?(?:file\s+)?" + SLOT1, re.I),
    "depth": re.compile(LEAD + SLOT0 + r"\s+(?:to\s+depth\s+|at\s+depth\s+|)(?P<s1>\d+)(?:\s+levels?\s+deep)?", re.I),
    "range": re.compile(LEAD + r"(?:between|from)\s+(?P<s0>\d+)\s+(?:and|to)\s+(?P<s1>\d+)", re.I),
}


def guarded_request(text):
    if not text or len(text) > 1024 or any(c in text for c in "\n\r\x00"):
        return None
    request = normalize_request(text)
    request = re.sub(r"^(?:let\s+me\s+|i(?:'d|\s+would)\s+like\s+to\s+|i\s+(?:want|need)\s+to\s+)", "", request, flags=re.I)
    request = re.sub(r"^i\s+(?:want|need)\s+(?:a\s+)?list\s+of\s+", "list ", request, flags=re.I)
    if request.lower().startswith("mind "):
        request = request[5:]
        verb, _, rest = request.partition(" ")
        if verb.lower().endswith("ing"):
            stem = verb.lower()[:-3]
            for lemma in (stem, stem + "e", stem[:-1] if len(stem) > 1 and stem[-1] == stem[-2] else ""):
                if lemma and REQUEST_START.fullmatch(lemma):
                    request = lemma + " " + rest
                    break
    visible = QUOTED.sub(" literal ", request).replace("\u2019", "'")
    if re.search(r"[;|&<>`$%\n\r]", visible):
        return None
    visible = re.sub(r"\bbetween\s+\d+\s+and\s+\d+\b", " range ", visible, flags=re.I)
    visible = LITERAL.sub(" literal ", visible)
    if BLOCK.search(visible) or re.search(r"\b\w+n't\b", visible, re.I) or not REQUEST_START.search(request):
        return None
    if re.match(r"define\b", visible, re.I) and not re.search(r"\b(?:alias|shortcut|variable)\b", visible, re.I):
        return None
    if re.search(r"\bhow\s+(?!(?:much|many|long)\b)", visible, re.I):
        return None
    if re.search(r"\b(?:and|or)\b", visible, re.I):
        return None
    # Do not turn an invalid/wildcard/punctuated path into another target.
    return request.strip()


def slot(raw, kind):
    quoted = len(raw) > 1 and raw[0] == raw[-1] and raw[0] in "\"'"
    value = raw[1:-1] if quoted else raw
    try:
        quote_argument(value)
    except ValueError:
        return None
    if kind in {"path", "file"}:
        if not quoted and (value.casefold() in RESERVED_TARGETS or value.startswith("-")):
            return None
        return _slot_value(raw, "file_path" if kind == "file" else "path")
    if kind == "integer":
        return _slot_value(value, "integer")
    if kind == "seconds":
        return value if re.fullmatch(r"\d+(?:\.\d+)?", value) and 0 <= float(value) <= 60 else None
    if kind == "host":
        return _slot_value(value, "host") if "." in value or value.lower() == "localhost" else None
    if kind in {"name", "branch", "process"}:
        if (not quoted and value.casefold() in RESERVED_TARGETS) or value.startswith("-"):
            return None
        pattern = r"[A-Za-z_][\w-]*" if kind == "name" else r"[A-Za-z0-9_][\w./-]*"
        return value if re.fullmatch(pattern, value) else None
    if kind == "theme":
        from ui.themes import get_theme
        try:
            get_theme(value)
            return value
        except KeyError:
            return None
    if kind == "text":
        # Text must be explicitly delimited, never swallowed from trailing prose.
        return value if quoted else None
    if kind == "url":
        try:
            parsed = urlsplit(value)
            return value if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password else None
        except ValueError:
            return None
    if kind == "expression":
        if not re.fullmatch(r"[\d\s.+*/()-]+", value):
            return None
        try:
            nodes = ast.walk(ast.parse(value, mode="eval"))
            if all(isinstance(node, (ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
                                     ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                                     ast.Pow, ast.UAdd, ast.USub, ast.Load)) for node in nodes):
                return value
        except (SyntaxError, ValueError):
            pass
        return None
    if kind == "argv":
        if not quoted:
            return None
        parsed = CommandParser().parse_line(value)
        if len(parsed) != 1 or len(parsed[0].pipeline.commands) != 1:
            return None
        command = parsed[0].pipeline.commands[0]
        if command.redirect_path:
            return None
        return (command.name, *command.args)
    return None


def bind(intent, request):
    if intent.layout == "none":
        # A no-argument match must not drop a user-supplied literal target.
        if QUOTED.search(request) or LITERAL.search(request):
            return None
        if re.search(r"\b(?:named|called|except|only\s+files|sorted|matching)\b", request, re.I):
            return None
        scope = (re.search(r"\b(?:in|inside|under|at|from|to|on)\s+(.+?)[.!?]?$", request, re.I)
                 if intent.command in {"files", "folders", "tree", "disk"} else None)
        if scope and not re.fullmatch(
            r"(?:(?:the|this|my|our|current|working|user)\s+)*(?:current\s+|working\s+)?"
            r"(?:directory|folder|location|computer|PC|machine|system|terminal|shell|console|"
            r"Git\s+remote|remote\s+repository|this\s+branch|piped\s+input|previous\s+output|home\s+(?:directory|folder))",
            scope[1], re.I,
        ):
            return None
        return intent.arguments, request
    pattern = LAYOUTS.get(intent.layout)
    match = pattern.fullmatch(request) if pattern else None
    captures = []
    if intent.layout == "one":
        # A single explicit literal may occur anywhere in the sentence. Keep
        # the entire surrounding instruction for semantic ranking.
        atoms = list(re.finditer(ATOM, request))
        strong = [m for m in atoms if QUOTED.fullmatch(m[0]) or LITERAL.fullmatch(m[0])]
        if len(strong) == 1 and re.fullmatch(TRAILER, request[strong[0].end():], re.I):
            captures = [(strong[0][0], strong[0].span())]
        if not captures and intent.command == "which":
            symbol = re.search(r"\b(?P<name>[A-Za-z_][\w-]*)\s+(?:executable|program|command)\s+(?:lives|resides|is\s+located)\b", request, re.I)
            if symbol:
                captures = [(symbol["name"], symbol.span("name"))]
    if not captures:
        if match is None:
            return None
        captures = [(match[f"s{i}"], match.span(f"s{i}")) for i in range(len(intent.kinds))]
    values = []
    spans = []
    for index, kind in enumerate(intent.kinds):
        raw, span = captures[index]
        value = slot(raw, kind)
        if value is None:
            return None
        if kind == "path" and intent.command in {"delete", "open", "makefolder", "shift", "duplicate", "rename"}:
            if not (QUOTED.search(request) or LITERAL.search(request)
                    or re.search(r"\b(?:file|folder|directory|document)\b", request, re.I)):
                return None
        values.append(value)
        spans.append((*span, "target" if len(intent.kinds) == 1 else ("source" if index == 0 else "destination")))
    masked = request
    for start, end, label in reversed(spans):
        masked = masked[:start] + label + masked[end:]
    # Every quoted string, path and number must belong to a validated slot.
    if QUOTED.search(masked) or LITERAL.search(masked):
        return None
    if intent.key == "random_range" and int(values[0]) > int(values[1]):
        return None
    if intent.command == "echo" and not re.search(r"\b(?:terminal|console|echo)\b", masked, re.I):
        return None
    if intent.command == "read" and not re.search(r"\b(?:print|display|verbatim|raw)\b", masked, re.I):
        return None
    if intent.command == "hash" and re.search(r"\b(?:md5|sha1|sha512)\b", masked, re.I):
        return None
    if intent.command == "gcheckout" and re.search(r"\b(?:file|restore)\b", masked, re.I):
        return None
    args = []
    for arg in intent.arguments:
        if arg.startswith("*"):
            args.extend(values[int(arg[1:])])
        else:
            args.append(values[int(arg[1:-1])] if arg.startswith("{") else arg)
    return tuple(args), masked


def compatible(intent, text):
    """Distinguish opposites that embedding similarity alone often confuses.

These are capability constraints, not sentence templates. Text/filenames have
already been masked, so words inside literal arguments cannot affect intent.
"""
    words = set(re.findall(r"[a-z]+", text.lower()))
    command = intent.command
    if "only" in words and command not in {"folders", "head", "tail", "take"}:
        return False
    if intent.layout == "none" and command in {
        "help", "plugins", "where", "files", "folders", "network", "processes", "system",
        "me", "pc", "today", "now", "history", "env", "tree", "version", "drives", "disk",
        "ip", "netstat", "path", "memory", "uptime", "vars", "alias", "theme",
        "gstatus", "gbranch", "glog", "gdiff", "gremote",
    } and words.intersection({"delete", "remove", "erase", "kill", "stop", "create", "make",
                              "switch", "checkout", "rename", "move", "assign", "apply", "set"}):
        return False
    gates = {
        "head": {"first", "top", "beginning", "start", "initial"},
        "tail": {"last", "bottom", "end", "ending", "final"},
        "take": {"first", "top", "beginning", "start", "initial"},
        "skip": {"skip", "omit", "drop", "discard"},
        "search": {"name", "names", "filename", "filenames", "named"},
        "findtext": {"inside", "contents", "content", "text", "phrase"},
        "filter": {"line", "lines", "output", "piped"},
        "gcheckout": {"switch", "checkout", "check", "change"},
        "gadd": {"stage", "staging", "add"},
        "gbranch": {"branch", "branches"},
        "glog": {"commit", "commits", "history", "log"},
        "gdiff": {"diff", "unstaged", "changes", "changed"},
        "gcommit": {"commit"},
        "gpull": {"pull", "bring", "fetch", "download"},
        "gpush": {"push", "upload", "publish", "send"},
        "unsetvar": {"remove", "unset", "delete", "erase"},
        "unalias": {"remove", "unset", "delete", "erase"},
        "delete": {"delete", "remove", "erase", "discard"},
        "kill": {"stop", "terminate", "kill", "end"},
        "shift": {"move", "relocate", "transfer"},
        "duplicate": {"copy", "duplicate", "backup", "back"},
        "rename": {"rename", "name", "filename"},
        "unzip": {"unzip", "unpack", "extract", "decompress"},
        "zip": {"zip", "compress", "package", "archive"},
        "makefile": {"empty", "blank"},
        "exit": {"terminal", "shell", "riftshell"},
        "up": {"up", "higher", "parent", "level"},
        "home": {"home"},
        "tree": {"tree", "hierarchy", "structure"},
        "last": {"print", "display", "show", "redisplay", "repeat", "again"},
    }
    if command in gates and not words.intersection(gates[command]):
        return False
    if intent.key == "base64_decode":
        return bool(words & {"decode", "back"})
    if intent.key == "base64_encode":
        return not words.intersection({"decode", "back"}) and bool(words & {"encode", "convert"})
    if command == "which" and words.intersection({"environment", "variable", "version"}):
        return False
    if command in {"unsetvar", "setvar"} and not words.intersection({"variable", "variables"}):
        return False
    if command in {"alias", "unalias"} and not words.intersection({"alias", "aliases", "shortcut", "shortcuts"}):
        return False
    if command == "open" and words.intersection({"navigate", "switch", "working"}):
        return False
    if command == "folders" and not words.intersection({"folders", "directories", "subdirectories"}):
        return False
    if command == "files" and words.intersection({"subdirectories", "directories", "folders"}) and not words.intersection({"files", "items", "everything", "contents"}):
        return False
    if command in {"files", "folders"} and words.intersection({"working", "currently"}) and words.intersection({"we", "i", "am"}):
        return False
    if command == "run" and words.intersection({"file", "script"}):
        # Native literal argv still needs the user's explicit command/program framing.
        return bool(words & {"command", "program", "native"})
    return True


_INDEX_LOCK = RLock()


def valid_spec(item):
    """Ignore malformed plugin declarations without weakening other commands."""
    if not isinstance(item, SemanticIntent):
        return False
    if any(not isinstance(value, str) or not value for value in (item.key, item.command, item.layout)):
        return False
    arity = {"none": 0, "one": 1, "location": 1, "pair": 2, "search": 2,
             "lines": 2, "depth": 2, "range": 2}.get(item.layout)
    kinds = {"path", "file", "integer", "seconds", "host", "name", "branch",
             "process", "text", "url", "expression", "argv", "theme"}
    if (arity is None or not isinstance(item.examples, tuple) or not item.examples
            or len(item.examples) > 8
            or any(not isinstance(text, str) or not text.strip() or len(text) > 256 for text in item.examples)
            or not isinstance(item.kinds, tuple) or len(item.kinds) != arity
            or any(not isinstance(kind, str) or kind not in kinds for kind in item.kinds)
            or not isinstance(item.arguments, tuple) or len(item.arguments) > 8):
        return False
    for arg in item.arguments:
        if not isinstance(arg, str):
            return False
        reference = re.fullmatch(r"\{(\d+)\}|\*(\d+)", arg)
        if reference:
            index = int(reference[1] or reference[2])
            if index >= arity or (reference[2] is not None) != (item.kinds[index] == "argv"):
                return False
        else:
            try:
                quote_argument(arg)
            except ValueError:
                return False
            if any(char in arg for char in "{}*"):
                return False
    return True


@lru_cache(maxsize=8)
def _index(intents):
    encoder = local_encoder()
    if encoder is None:
        return None
    with _INDEX_LOCK:
        sentences = [text for intent in intents for text in intent.examples] + list(CHAT_EXAMPLES)
        # Bounded batches avoid excessive padding and temporary memory.
        vectors = encoder.np.concatenate([encoder.encode(sentences[i:i+16]) for i in range(0, len(sentences), 16)])
        owners = [i for i, intent in enumerate(intents) for _ in intent.examples]
        owners += [-1] * len(CHAT_EXAMPLES)
        return encoder, vectors, owners


class SemanticIntentExtractor:
    MIN_SCORE = 0.64
    MIN_MARGIN = 0.07

    def __init__(self, names, metadata=()):
        self.names = frozenset(names)
        metadata = tuple(metadata)
        metas = {meta.name: meta for meta in metadata}
        definitions = []
        for item in SEMANTIC_INTENTS:
            if item.command not in self.names:
                continue
            meta = metas.get(item.command)
            # Built-in Git/hello capabilities belong only to bundled plugins.
            expected_plugin = "git" if item.command.startswith("g") and item.command != "goto" else "hello" if item.command == "hello" else None
            if meta and meta.source == "plugin" and meta.plugin != expected_plugin:
                continue
            definitions.append(item)
        for meta in metadata:
            declared = meta.extra.get("orbit_semantics", ())
            if isinstance(declared, (tuple, list)):
                definitions.extend(item for item in declared if valid_spec(item)
                                   and item.command == meta.name and item.command in self.names)
        self.intents = tuple(definitions)

    def rank(self, text):
        request = guarded_request(text)
        if request is None:
            return []
        bindings = [(i, item, bound) for i, item in enumerate(self.intents)
                    if (bound := bind(item, request)) is not None and compatible(item, bound[1])]
        if not bindings:
            return []
        try:
            index = _index(self.intents)
            if index is None:
                return []
            encoder, vectors, owners = index
            queries = list(dict.fromkeys(bound[1] for _, _, bound in bindings))
            scores = encoder.encode(queries) @ vectors.T
        except Exception:
            return []
        rows = dict(zip(queries, scores))
        # Include plausible interpretations whose arguments could not be bound.
        # A missing branch name must not turn "switch branch" into "list branches".
        competitors = {
            query: {i: max(float(value) for value, owner in zip(rows[query], owners) if owner == i)
                    for i, item in enumerate(self.intents) if compatible(item, query)}
            for query in queries
        }
        ranked = {}
        for i, intent, (args, query) in bindings:
            row = rows[query]
            score = max(float(value) for value, owner in zip(row, owners) if owner == i)
            chat_score = max(float(value) for value, owner in zip(row, owners) if owner == -1)
            if not math.isfinite(score) or score < chat_score + self.MIN_MARGIN:
                continue
            if any(other_score > score + self.MIN_MARGIN
                   for owner, other_score in competitors[query].items()
                   if self.intents[owner].command != intent.command):
                continue
            candidate = CommandCandidate(intent.key, intent.command, args,
                                         f"I will run {intent.command} for this request.",
                                         source="local_semantic", confidence=score)
            if not valid_candidate(candidate, self.names):
                continue
            previous = ranked.get(candidate.command)
            if previous is None or previous.confidence < score:
                ranked[candidate.command] = candidate
        return sorted(ranked.values(), key=lambda item: item.confidence, reverse=True)

    def extract(self, text):
        ranked = self.rank(text)
        if not ranked or ranked[0].confidence < self.MIN_SCORE:
            return Extraction()
        if len(ranked) > 1 and ranked[0].confidence - ranked[1].confidence < self.MIN_MARGIN:
            return Extraction("ambiguous", tuple(ranked[:3]))
        return Extraction("matched", (ranked[0],))


class HybridIntentExtractor:
    """Preserve deterministic matches; rank unfamiliar English locally."""
    def __init__(self, names, *, metadata=()):
        names, metadata = tuple(names), tuple(metadata)
        self.rules = RuleIntentExtractor(names, metadata=metadata)
        self.semantic = SemanticIntentExtractor(names, metadata)

    def extract(self, text):
        result = self.rules.extract(text)
        if result.status != "no_match":
            return result
        return self.semantic.extract(text)

    @staticmethod
    def permits(candidate):
        return (candidate.source == "local_semantic" and math.isfinite(candidate.confidence)
                and SemanticIntentExtractor.MIN_SCORE <= candidate.confidence <= 1.00001)
