"""Install the pinned Apache-2.0 MiniLM ONNX model; never called during chat."""
from pathlib import Path
import hashlib
import urllib.request


REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
BASE = f"https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/{REVISION}/"
DESTINATION = Path(__file__).resolve().parent.parent / "assets" / "intent-model"
FILES = (
    ("onnx/model_quint8_avx2.onnx", "model.onnx", "sha256", "b941bf19f1f1283680f449fa6a7336bb5600bdcd5f84d10ddc5cd72218a0fd21"),
    ("tokenizer.json", "tokenizer.json", "git", "cb202bfe2e3c98645018a6d12f182a434c9d3e02"),
    ("README.md", "MODEL_CARD.md", "git", "44af2e3b0fa3a0b6239e48422972bf755f28fde0"),
    ("https://www.apache.org/licenses/LICENSE-2.0.txt", "LICENSE.txt", "sha256", "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"),
)


def digest(data, kind):
    if kind == "sha256":
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for remote, name, kind, expected in FILES:
        target = DESTINATION / name
        if target.is_file() and digest(target.read_bytes(), kind) == expected:
            print(f"Verified {name}")
            continue
        print(f"Downloading checksum-pinned {name}...", flush=True)
        url = remote if remote.startswith("https://") else BASE + remote
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(100_000_000)
        if digest(data, kind) != expected:
            raise RuntimeError(f"Checksum mismatch for {name}; installation stopped")
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(target)
    print(f"Offline intent model ready: {DESTINATION}")


if __name__ == "__main__":
    main()
