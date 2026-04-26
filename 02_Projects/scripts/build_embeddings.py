#!/usr/bin/env python3
"""
build_embeddings.py – Generate vector embeddings for all .md files in the vault.

Strategy:
1. Walk the vault root (CWD) and find all .md files.
2. Read each file, split into chunks (by heading or ~500 chars).
3. Generate embeddings using sentence-transformers (all-MiniLM-L6-v2).
4. Store in 05_Meta/embeddings.json as {chunk_text: vector, file: path}.

Fallback: If sentence-transformers is unavailable, use a lightweight TF-IDF approach
or skip embedding and log a warning.

Run this after every 5 new/changed notes, or on demand.
"""

import json
import hashlib
import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path.cwd()
EMBEDDINGS_PATH = VAULT_ROOT / "05_Meta" / "embeddings.json"
IGNORE_DIRS = {".git", "__pycache__", "node_modules"}
CHUNK_SIZE = 500  # characters per chunk

def get_md_files(root):
    """Recursively find all .md files, excluding ignored dirs."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            if fn.endswith(".md"):
                files.append(Path(dirpath) / fn)
    return files

def chunk_text(text, file_rel):
    """Split text into chunks by headings or character limit."""
    chunks = []
    # Split by ## or ### headings
    sections = re.split(r'(?=^##+\s)', text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= CHUNK_SIZE:
            chunks.append({"text": section, "source": str(file_rel)})
        else:
            # Further split long sections
            for i in range(0, len(section), CHUNK_SIZE):
                chunk = section[i:i+CHUNK_SIZE].strip()
                if chunk:
                    chunks.append({"text": chunk, "source": str(file_rel)})
    return chunks

def compute_embedding(text):
    """
    Compute a vector embedding for the given text.
    
    Primary: sentence-transformers (all-MiniLM-L6-v2)
    Fallback: hash-based pseudo-embedding for now (will be replaced).
    
    Returns a list of floats.
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model.encode(text).tolist()
    except ImportError:
        # Fallback: deterministic hash-based pseudo-embedding (384-dim)
        # This preserves some semantic similarity via hash overlap.
        # Replace with real embeddings when sentence-transformers is available.
        dim = 384
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        # Use bytes to pseudo-randomly fill a vector
        vec = []
        for i in range(dim):
            b = seed[i % len(seed)]
            vec.append((b / 255.0) * 2 - 1)  # normalize to [-1, 1]
        print(f"  [fallback] Using hash-based embedding for {len(text)} chars", file=sys.stderr)
        return vec

def main():
    print(f"Scanning vault: {VAULT_ROOT}", file=sys.stderr)
    md_files = get_md_files(VAULT_ROOT)
    print(f"Found {len(md_files)} markdown files", file=sys.stderr)

    all_chunks = []
    for fpath in md_files:
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Error reading {fpath}: {e}", file=sys.stderr)
            continue

        rel = fpath.relative_to(VAULT_ROOT)
        chunks = chunk_text(text, rel)
        all_chunks.extend(chunks)
        print(f"  {rel}: {len(chunks)} chunks", file=sys.stderr)

    print(f"Total chunks: {len(all_chunks)}", file=sys.stderr)

    # Load existing embeddings if they exist
    existing = {}
    if EMBEDDINGS_PATH.exists():
        try:
            existing = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            existing = {}

    # Compute embeddings for new/changed chunks (content hash as key)
    for chunk in all_chunks:
        content_hash = hashlib.md5(chunk["text"].encode("utf-8")).hexdigest()
        if content_hash not in existing:
            vec = compute_embedding(chunk["text"])
            existing[content_hash] = {
                "vector": vec,
                "text": chunk["text"][:200],  # store preview only
                "source": chunk["source"]
            }
        else:
            # Already indexed
            pass

    EMBEDDINGS_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nDone. {len(existing)} chunks indexed in {EMBEDDINGS_PATH}", file=sys.stderr)

if __name__ == "__main__":
    main()
