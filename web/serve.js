#!/usr/bin/env node
/**
 * serve.js — StreamMuter local dev server
 * Sirve los archivos estáticos en localhost y muestra un QR en la consola.
 * Uso: node serve.js
 */

const http    = require('http');
const fs      = require('fs');
const path    = require('path');
const os      = require('os');
const qr      = require('qrcode-terminal');

const PORT = 3000;
const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

// ── Server ──────────────────────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/streammuter.html';

  const filePath = path.resolve(ROOT, '.' + urlPath);

  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not found');
      return;
    }
    const ext  = path.extname(filePath).toLowerCase();
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  });
});

// ── Helpers ──────────────────────────────────────────────────────────────────
function getLocalIp() {
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const iface of ifaces) {
      if (iface.family === 'IPv4' && !iface.internal) return iface.address;
    }
  }
  return '127.0.0.1';
}

// ── Start ────────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  const localUrl   = `http://localhost:${PORT}`;
  const networkUrl = `http://${getLocalIp()}:${PORT}`;

  const R  = '\x1b[0m';
  const B  = '\x1b[1m';
  const DIM= '\x1b[2m';
  const P  = '\x1b[35m';
  const C  = '\x1b[36m';
  const G  = '\x1b[32m';
  const Y  = '\x1b[33m';

  console.clear();
  console.log(`\n${B}${P}  ╔══════════════════════════════════════╗${R}`);
  console.log(`${B}${P}  ║  ${C}StreamMuter${P}  — servidor local      ║${R}`);
  console.log(`${B}${P}  ╚══════════════════════════════════════╝${R}\n`);

  console.log(`  ${DIM}Escanea con tu móvil (misma red WiFi):${R}\n`);

  // QR del URL de red local (para móvil)
  qr.generate(networkUrl, { small: true });

  console.log(`  ${DIM}Local  :${R}  ${B}${G}${localUrl}${R}`);
  console.log(`  ${DIM}Red    :${R}  ${B}${C}${networkUrl}${R}`);
  console.log(`\n  ${Y}Ctrl+C${R} para detener.\n`);
});
