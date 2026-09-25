"""Offline sentence embeddings. No downloads or cloud calls on the request path."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from threading import RLock
import os


MODEL_DIR = Path(__file__).resolve().parent.parent / "assets" / "intent-model"


class LocalIntentEncoder:
    def __init__(self, directory: Path):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.np = np
        self.lock = RLock()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "model.onnx"), sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self.inputs = {item.name for item in self.session.get_inputs()}

    def encode(self, texts):
        with self.lock:
            encoded = self.tokenizer.encode_batch(list(texts))
            # Never silently truncate an instruction: a trailing constraint matters.
            if any(len(item.ids) > 256 for item in encoded):
                raise ValueError("Request exceeds semantic encoder context")
            np = self.np
            ids = np.asarray([item.ids for item in encoded], dtype=np.int64)
            mask = np.asarray([item.attention_mask for item in encoded], dtype=np.int64)
            types = np.asarray([item.type_ids for item in encoded], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
            hidden = self.session.run(None, {key: value for key, value in feed.items() if key in self.inputs})[0]
            weights = mask[:, :, None]
            pooled = (hidden * weights).sum(axis=1) / weights.sum(axis=1).clip(min=1)
            return pooled / np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-9)


@lru_cache(maxsize=1)
def local_encoder():
    if os.getenv("RIFT_SEMANTIC_INTENTS", "1").lower() in {"0", "false", "off"}:
        return None
    if not all((MODEL_DIR / name).is_file() for name in ("model.onnx", "tokenizer.json")):
        return None
    try:
        return LocalIntentEncoder(MODEL_DIR)
    except Exception:
        # Optional runtime/model failures must not disable the original router.
        return None
