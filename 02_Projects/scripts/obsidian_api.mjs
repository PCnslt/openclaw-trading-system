/**
 * obsidian_api.mjs — Obsidian Local REST API helper
 * 
 * Usage:
 *   node 02_Projects/scripts/obsidian_api.mjs list          # list all files
 *   node 02_Projects/scripts/obsidian_api.mjs search <q>   # search vault
 *   node 02_Projects/scripts/obsidian_api.mjs read <path>  # read a file
 *   node 02_Projects/scripts/obsidian_api.mjs today        # create/open daily note
 *   node 02_Projects/scripts/obsidian_api.mjs recent        # recent files
 */

import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pluginDir = path.resolve(__dirname, '../../.obsidian/plugins/obsidian-local-rest-api');
const configPath = path.join(pluginDir, 'data.json');

const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
const API_KEY = config.apiKey;
const PORT = config.port || 27123;

function apiRequest(method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: '127.0.0.1',
      port: PORT,
      path: apiPath,
      method: method,
      rejectUnauthorized: false,
      headers: {
        'Authorization': 'Bearer ' + API_KEY,
        'Content-Type': 'application/json'
      }
    };
    const req = https.request(opts, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function listFiles() {
  const data = await apiRequest('GET', '/vault/');
  console.log('Vault files (' + data.files?.length + ' total):');
  data.files?.forEach(f => {
    const isDir = f.endsWith('/');
    console.log(isDir ? '  📁 ' + f : '  📄 ' + f);
  });
}

async function searchVault(query) {
  const data = await apiRequest('GET', '/search/?query=' + encodeURIComponent(query));
  console.log('Search results for "' + query + '":');
  (data.results || data || []).forEach(r => {
    const filename = r.filename || r.path || '?';
    const score = r.score ? ' (score: ' + r.score.toFixed(2) + ')' : '';
    console.log('  ' + filename + score);
  });
}

async function readFile(filepath) {
  const data = await apiRequest('GET', '/vault/' + encodeURIComponent(filepath));
  if (data.content) {
    console.log(data.content);
  } else {
    console.log(JSON.stringify(data, null, 2));
  }
}

async function recentFiles() {
  const data = await apiRequest('GET', '/vault/');
  // Sort by modification time if available
  console.log('Recent files:');
  data.files?.slice(-10).reverse().forEach(f => console.log('  ' + f));
}

const cmd = process.argv[2];
const arg = process.argv[3];

switch (cmd) {
  case 'list': listFiles().catch(e => console.error('Error:', e.message)); break;
  case 'search': searchVault(arg || '').catch(e => console.error('Error:', e.message)); break;
  case 'read': readFile(arg || '').catch(e => console.error('Error:', e.message)); break;
  case 'recent': recentFiles().catch(e => console.error('Error:', e.message)); break;
  default:
    console.log('Usage: node obsidian_api.mjs <list|search|read|recent> [arg]');
}
