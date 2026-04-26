#!/usr/bin/env node
/**
 * build_embeddings.mjs
 * Generate vector embeddings for all .md files in the vault using Transformers.js.
 *
 * Strategy:
 * 1. Walk the vault root (CWD) and find all .md files.
 * 2. Read each file, split into chunks (by heading or ~500 chars).
 * 3. Generate embeddings using all-MiniLM-L6-v2 via @xenova/transformers.
 * 4. Store in 05_Meta/embeddings.json as {chunkHash: {vector, text, source}}.
 *
 * Usage: node 02_Projects/scripts/build_embeddings.mjs
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const VAULT_ROOT = process.cwd();
const EMBEDDINGS_PATH = path.join(VAULT_ROOT, '05_Meta', 'embeddings.json');
const IGNORE_DIRS = new Set(['.git', '__pycache__', 'node_modules']);
const CHUNK_SIZE = 500;

function getMDFiles(dir) {
  const files = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (!IGNORE_DIRS.has(entry.name)) {
          files.push(...getMDFiles(path.join(dir, entry.name)));
        }
      } else if (entry.name.endsWith('.md')) {
        files.push(path.join(dir, entry.name));
      }
    }
  } catch {}
  return files;
}

function chunkText(text, fileRel) {
  const chunks = [];
  const sections = text.split(/(?=^##+\s)/m);
  for (const section of sections) {
    const trimmed = section.trim();
    if (!trimmed) continue;
    if (trimmed.length <= CHUNK_SIZE) {
      chunks.push({ text: trimmed, source: fileRel });
    } else {
      for (let i = 0; i < trimmed.length; i += CHUNK_SIZE) {
        const chunk = trimmed.slice(i, i + CHUNK_SIZE).trim();
        if (chunk) chunks.push({ text: chunk, source: fileRel });
      }
    }
  }
  return chunks;
}

async function getExtractor() {
  try {
    const { pipeline } = await import('@xenova/transformers');
    const extract = await pipeline('feature-extraction', 'all-MiniLM-L6-v2');
    return extract;
  } catch (e) {
    console.error(`[transformers] ${e.message || e}`);
    console.error('[info] Falling back to hash-based pseudo-embeddings.');
    return null;
  }
}

async function main() {
  console.error(`Scanning vault: ${VAULT_ROOT}`);
  const mdFiles = getMDFiles(VAULT_ROOT);
  console.error(`Found ${mdFiles.length} markdown files`);

  const allChunks = [];
  for (const fpath of mdFiles) {
    try {
      const text = fs.readFileSync(fpath, 'utf-8');
      const rel = path.relative(VAULT_ROOT, fpath);
      const chunks = chunkText(text, rel);
      allChunks.push(...chunks);
      console.error(`  ${rel}: ${chunks.length} chunks`);
    } catch (e) {
      console.error(`  Error reading ${fpath}: ${e.message}`);
    }
  }
  console.error(`Total chunks: ${allChunks.length}`);

  let existing = {};
  try {
    existing = JSON.parse(fs.readFileSync(EMBEDDINGS_PATH, 'utf-8'));
  } catch {}

  const extract = await getExtractor();

  for (const chunk of allChunks) {
    const contentHash = crypto.createHash('md5').update(chunk.text).digest('hex');
    if (existing[contentHash]) continue;

    let useExtract = extract;
    let vector;
    if (useExtract) {
      try {
        const result = await useExtract(chunk.text, { pooling: 'mean', normalize: true });
        vector = Array.from(result.data);
        console.error(`  [transformers] Embedded ${chunk.text.length} chars -> ${vector.length} dims`);
      } catch (e) {
        console.error(`  [transformers error] ${e.message}; falling back`);
        useExtract = null;  // disable for remaining chunks
        extract = null;
        vector = null;
      }
    }

    if (!vector) {
      const dim = 384;
      const seed = crypto.createHash('sha256').update(chunk.text).digest();
      vector = [];
      for (let i = 0; i < dim; i++) {
        vector.push((seed[i % seed.length] / 255) * 2 - 1);
      }
    }

    existing[contentHash] = {
      vector,
      text: chunk.text.slice(0, 200),
      source: chunk.source
    };
  }

  fs.writeFileSync(EMBEDDINGS_PATH, JSON.stringify(existing, null, 2), 'utf-8');
  console.error(`\nDone. ${Object.keys(existing).length} chunks indexed in ${EMBEDDINGS_PATH}`);
}

main().catch(console.error);
