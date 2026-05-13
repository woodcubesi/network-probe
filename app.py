#!/usr/bin/env python3
"""
Web network probe for TCP, UDP, and ICMP tests.

Run:
    python app.py

Then open:
    http://127.0.0.1:8081
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


DEFAULT_HOST = "google.com"
DEFAULT_PROTOCOL = "tcp"
DEFAULT_PORT = 443
DEFAULT_COUNT = 4
DEFAULT_TIMEOUT = 2.0
DEFAULT_INTERVAL = 1.0

MAX_COUNT = 100
MIN_TIMEOUT = 0.1
MAX_TIMEOUT = 30.0
MIN_INTERVAL = 0.0
MAX_INTERVAL = 30.0
MAX_SCAN_PORTS = 2048
MAX_SCAN_CONCURRENCY = 512


INDEX_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Network Probe</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #1a202c;
      --muted: #667085;
      --line: #d8dee9;
      --good: #087443;
      --bad: #b42318;
      --accent: #175cd3;
      --accent-dark: #0b4db3;
      --chip: #edf3ff;
      --shadow: 0 16px 44px rgba(29, 41, 57, 0.10);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }

    main {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 42px;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0 0 6px;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      color: var(--muted);
      white-space: nowrap;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #98a2b3;
    }

    .dot.running {
      background: #f79009;
    }

    .dot.ok {
      background: var(--good);
    }

    .dot.fail {
      background: var(--bad);
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr;
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    form.panel {
      padding: 18px;
      display: grid;
      gap: 14px;
    }

    label {
      display: grid;
      gap: 7px;
      color: #344054;
      font-size: 13px;
      font-weight: 700;
    }

    input,
    select {
      width: 100%;
      min-height: 42px;
      padding: 9px 11px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      font-size: 15px;
      outline: none;
    }

    input:focus,
    select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(23, 92, 211, 0.14);
    }

    input:disabled,
    select:disabled {
      background: #f1f5f9;
      color: #98a2b3;
    }

    .segmented {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 4px;
      padding: 4px;
      border: 1px solid #d0d5dd;
      border-radius: 6px;
      background: #eef2f7;
    }

    .segmented.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .segmented label {
      display: block;
      margin: 0;
      font-size: 13px;
      font-weight: 800;
      color: #475467;
      cursor: pointer;
    }

    .segmented input {
      position: absolute;
      width: 1px;
      height: 1px;
      min-height: 1px;
      opacity: 0;
      pointer-events: none;
    }

    .segmented span {
      display: grid;
      place-items: center;
      min-height: 34px;
      border-radius: 5px;
    }

    .segmented input:checked + span {
      background: #ffffff;
      color: var(--accent);
      box-shadow: 0 1px 3px rgba(29, 41, 57, 0.14);
    }

    .toggle-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 42px;
      padding: 9px 11px;
      border: 1px solid #d0d5dd;
      border-radius: 6px;
      background: #f8fafc;
      color: #344054;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }

    .toggle-row input {
      width: 18px;
      height: 18px;
      min-height: 18px;
      margin: 0;
      accent-color: var(--accent);
      cursor: pointer;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .actions {
      display: grid;
      grid-template-columns: 1fr 44px;
      gap: 10px;
      align-items: center;
      margin-top: 2px;
    }

    button {
      border: 0;
      border-radius: 6px;
      min-height: 44px;
      font-size: 15px;
      font-weight: 800;
      cursor: pointer;
    }

    .primary {
      background: var(--accent);
      color: white;
    }

    .primary:hover {
      background: var(--accent-dark);
    }

    .secondary {
      display: inline-grid;
      place-items: center;
      background: #eef2f7;
      color: #344054;
      font-size: 20px;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.62;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      padding: 14px;
      border-bottom: 1px solid var(--line);
    }

    .metric {
      min-height: 78px;
      padding: 12px;
      background: #f8fafc;
      border: 1px solid #e4e7ec;
      border-radius: 6px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .metric strong {
      display: block;
      margin-top: 8px;
      font-size: 22px;
      line-height: 1;
      word-break: break-word;
    }

    .output-wrap {
      padding: 14px;
    }

    .console {
      min-height: 210px;
      max-height: 360px;
      overflow: auto;
      padding: 13px;
      background: #111827;
      color: #d1d5db;
      border-radius: 6px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
    }

    .console .ok {
      color: #86efac;
    }

    .console .fail {
      color: #fca5a5;
    }

    .console .info {
      color: #bfdbfe;
    }

    .table-wrap {
      overflow: auto;
      border-top: 1px solid var(--line);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 620px;
      font-size: 14px;
    }

    th,
    td {
      padding: 12px 14px;
      border-bottom: 1px solid #eaecf0;
      text-align: left;
      vertical-align: middle;
    }

    th {
      background: #f8fafc;
      color: #475467;
      font-size: 12px;
      text-transform: uppercase;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 800;
    }

    .badge.ok {
      background: #dcfae6;
      color: var(--good);
    }

    .badge.fail {
      background: #fee4e2;
      color: var(--bad);
    }

    .badge.unknown {
      background: #fef0c7;
      color: #93370d;
    }

    .hint {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    @media (max-width: 840px) {
      header,
      .layout {
        grid-template-columns: 1fr;
      }

      header {
        align-items: flex-start;
      }

      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 520px) {
      main {
        width: min(100% - 20px, 1120px);
        padding-top: 18px;
      }

      .grid-2,
      .actions,
      .summary {
        grid-template-columns: 1fr;
      }

      .secondary {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Network Probe</h1>
        <p class="subtitle">Teste TCP, UDP e ICMP com latencia, perda e jitter.</p>
      </div>
      <div class="status-pill" aria-live="polite">
        <span id="statusDot" class="dot"></span>
        <span id="statusText">Pronto</span>
      </div>
    </header>

    <div class="layout">
      <form id="probeForm" class="panel">
        <label>
          Host ou IP
          <input id="host" name="host" value="google.com" placeholder="ex: 192.168.0.1 ou google.com" required />
        </label>

        <div>
          <label>Modo</label>
          <div class="segmented two" role="radiogroup" aria-label="Modo">
            <label>
              <input type="radio" name="mode" value="probe" checked />
              <span>Teste</span>
            </label>
            <label>
              <input type="radio" name="mode" value="scan" />
              <span>Port Scan</span>
            </label>
          </div>
        </div>

        <div>
          <label>Protocolo</label>
          <div id="protocolGroup" class="segmented" role="radiogroup" aria-label="Protocolo">
            <label>
              <input type="radio" name="protocol" value="tcp" checked />
              <span>TCP</span>
            </label>
            <label>
              <input type="radio" name="protocol" value="udp" />
              <span>UDP</span>
            </label>
            <label>
              <input type="radio" name="protocol" value="icmp" />
              <span>ICMP</span>
            </label>
          </div>
        </div>

        <div class="grid-2">
          <label id="portLabel">
            Porta
            <input id="port" name="port" inputmode="numeric" pattern="[0-9]*" value="443" required />
          </label>
          <label>
            Tentativas
            <input id="count" name="count" inputmode="numeric" pattern="[0-9]*" value="4" required />
          </label>
        </div>

        <div id="scanFields" hidden>
          <label>
            Portas para scan
            <input id="scanPorts" name="scan_ports" value="21,22,25,53,80,110,143,443,445,587,993,995,1433,3306,3389,5432,5900,8080,8081" placeholder="ex: 1-1024 ou 22,80,443,8000-8100" />
          </label>
          <div class="grid-2">
            <label>
              Concorrencia
              <input id="scanConcurrency" name="scan_concurrency" inputmode="numeric" pattern="[0-9]*" value="100" />
            </label>
            <label class="toggle-row">
              <input id="showClosed" name="show_closed" type="checkbox" value="1" />
              Mostrar fechadas
            </label>
          </div>
        </div>

        <label class="toggle-row">
          <input id="continuous" name="continuous" type="checkbox" value="1" />
          Teste continuo (-t)
        </label>

        <div class="grid-2">
          <label>
            Timeout (s)
            <input id="timeout" name="timeout" inputmode="decimal" value="2" required />
          </label>
          <label>
            Intervalo (s)
            <input id="interval" name="interval" inputmode="decimal" value="1" required />
          </label>
        </div>

        <div class="actions">
          <button class="primary" id="startBtn" type="submit">Iniciar teste</button>
          <button class="secondary" id="stopBtn" type="button" title="Parar" aria-label="Parar" disabled>&#9632;</button>
        </div>

        <p id="modeHint" class="hint">TCP mede o tempo para abrir uma conexao. UDP envia um datagrama e aguarda resposta; sem resposta pode significar porta silenciosa ou filtrada. ICMP usa ping do sistema.</p>
      </form>

      <section class="panel" aria-label="Resultado do teste">
        <div class="summary">
          <div class="metric"><span id="sentLabel">Enviadas</span><strong id="sent">0</strong></div>
          <div class="metric"><span id="successLabel">Sucesso</span><strong id="success">0</strong></div>
          <div class="metric"><span id="lossLabel">Perda</span><strong id="loss">0%</strong></div>
          <div class="metric"><span id="avgLabel">Media</span><strong id="avg">-</strong></div>
          <div class="metric"><span id="jitterLabel">Jitter</span><strong id="jitter">-</strong></div>
        </div>

        <div class="output-wrap">
          <div id="console" class="console" role="log" aria-live="polite">Aguardando teste...</div>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Status</th>
                <th>Latencia</th>
                <th>Jitter</th>
                <th>Endereco</th>
                <th>Mensagem</th>
                <th>Horario</th>
              </tr>
            </thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
      </section>
    </div>
  </main>

  <script>
    const form = document.querySelector("#probeForm");
    const startBtn = document.querySelector("#startBtn");
    const stopBtn = document.querySelector("#stopBtn");
    const consoleEl = document.querySelector("#console");
    const rows = document.querySelector("#rows");
    const statusDot = document.querySelector("#statusDot");
    const statusText = document.querySelector("#statusText");
    const sentEl = document.querySelector("#sent");
    const successEl = document.querySelector("#success");
    const lossEl = document.querySelector("#loss");
    const avgEl = document.querySelector("#avg");
    const jitterEl = document.querySelector("#jitter");
    const sentLabel = document.querySelector("#sentLabel");
    const successLabel = document.querySelector("#successLabel");
    const lossLabel = document.querySelector("#lossLabel");
    const avgLabel = document.querySelector("#avgLabel");
    const jitterLabel = document.querySelector("#jitterLabel");
    const modeInputs = document.querySelectorAll('input[name="mode"]');
    const protocolInputs = document.querySelectorAll('input[name="protocol"]');
    const protocolGroup = document.querySelector("#protocolGroup");
    const portInput = document.querySelector("#port");
    const portLabel = document.querySelector("#portLabel");
    const countInput = document.querySelector("#count");
    const continuousInput = document.querySelector("#continuous");
    const scanFields = document.querySelector("#scanFields");
    const scanPortsInput = document.querySelector("#scanPorts");
    const scanConcurrencyInput = document.querySelector("#scanConcurrency");
    const showClosedInput = document.querySelector("#showClosed");
    const modeHint = document.querySelector("#modeHint");

    const MAX_LOG_LINES = 500;
    const MAX_TABLE_ROWS = 500;
    let source = null;
    let stats = { sent: 0, success: 0, latencySum: 0, minLatency: null, maxLatency: null, lastLatency: null, jitterSum: 0, jitterSamples: 0 };

    function setStatus(kind, text) {
      statusDot.className = "dot" + (kind ? " " + kind : "");
      statusText.textContent = text;
    }

    function appendLine(text, className = "") {
      if (consoleEl.textContent === "Aguardando teste...") {
        consoleEl.textContent = "";
      }
      const line = document.createElement("div");
      line.className = className;
      line.textContent = text;
      consoleEl.appendChild(line);
      while (consoleEl.children.length > MAX_LOG_LINES) {
        consoleEl.removeChild(consoleEl.firstElementChild);
      }
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    function ms(value) {
      return value == null ? "-" : `${value.toFixed(2)} ms`;
    }

    function updateSummary(summary) {
      const data = summary || currentSummary();
      sentEl.textContent = data.sent;
      successEl.textContent = data.success;
      lossEl.textContent = `${data.loss_percent.toFixed(1)}%`;
      avgEl.textContent = ms(data.avg_ms);
      jitterEl.textContent = ms(data.jitter_ms);
    }

    function currentSummary() {
      const sent = stats.sent;
      const success = stats.success;
      const loss = sent ? ((sent - success) / sent) * 100 : 0;
      const avg = success
        ? stats.latencySum / success
        : null;
      return {
        sent,
        success,
        failed: sent - success,
        loss_percent: loss,
        min_ms: stats.minLatency,
        avg_ms: avg,
        max_ms: stats.maxLatency,
        jitter_ms: stats.jitterSamples ? stats.jitterSum / stats.jitterSamples : null,
      };
    }

    function appendSummary(prefix, summary = currentSummary()) {
      appendLine(`${prefix}: ${summary.success}/${summary.sent} sucesso, perda ${summary.loss_percent.toFixed(1)}%, min ${ms(summary.min_ms)}, media ${ms(summary.avg_ms)}, max ${ms(summary.max_ms)}, jitter ${ms(summary.jitter_ms)}`, "info");
    }

    function updateScanSummary(summary) {
      const data = summary || {
        tested: stats.sent,
        open: stats.success,
        closed: stats.sent - stats.success,
        progress_percent: 0,
        avg_ms: stats.success ? stats.latencySum / stats.success : null,
      };
      sentEl.textContent = data.tested;
      successEl.textContent = data.open;
      lossEl.textContent = data.closed;
      avgEl.textContent = ms(data.avg_ms);
      jitterEl.textContent = `${(data.progress_percent || 0).toFixed(1)}%`;
    }

    function appendScanSummary(prefix, summary) {
      appendLine(`${prefix}: ${summary.open}/${summary.total} portas abertas, ${summary.closed} fechadas/filtradas, media ${ms(summary.avg_ms)}`, "info");
    }

    function selectedMode() {
      return document.querySelector('input[name="mode"]:checked').value;
    }

    function selectedProtocol() {
      return document.querySelector('input[name="protocol"]:checked').value;
    }

    function protocolLabel(protocol = selectedProtocol()) {
      return protocol.toUpperCase();
    }

    function updateProtocolFields() {
      const mode = selectedMode();
      const isScan = mode === "scan";
      const protocol = selectedProtocol();
      const usesPort = !isScan && protocol !== "icmp";
      protocolGroup.style.opacity = isScan ? "0.55" : "1";
      portInput.disabled = !usesPort;
      portInput.required = usesPort;
      portLabel.style.opacity = usesPort ? "1" : "0.55";
      countInput.disabled = isScan || continuousInput.checked;
      continuousInput.disabled = isScan;
      scanFields.hidden = !isScan;
      scanPortsInput.required = isScan;
      scanConcurrencyInput.required = isScan;

      if (isScan) {
        sentLabel.textContent = "Testadas";
        successLabel.textContent = "Abertas";
        lossLabel.textContent = "Fechadas";
        avgLabel.textContent = "Media";
        jitterLabel.textContent = "Progresso";
        modeHint.textContent = "Port Scan faz conexoes TCP nas portas informadas e lista portas abertas. Use apenas em hosts autorizados.";
        return;
      }

      sentLabel.textContent = "Enviadas";
      successLabel.textContent = "Sucesso";
      lossLabel.textContent = "Perda";
      avgLabel.textContent = "Media";
      jitterLabel.textContent = "Jitter";
      modeHint.textContent = {
        tcp: "TCP mede o tempo para abrir uma conexao com a porta de destino.",
        udp: "UDP envia um datagrama e aguarda resposta; sem resposta pode significar porta silenciosa ou filtrada.",
        icmp: "ICMP usa o ping do sistema e nao utiliza porta."
      }[protocol];
    }

    function endpointText(result) {
      if (result.peer) {
        return result.peer;
      }
      if (result.attempts && result.attempts.length) {
        return result.attempts.map((attempt) => attempt.address).join(", ");
      }
      return "-";
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function addRow(result) {
      const tr = document.createElement("tr");
      const status = result.status || (result.ok ? "ok" : "fail");
      const statusClass = status === "unknown" ? "unknown" : (result.ok ? "ok" : "fail");
      const statusLabel = {
        ok: "OK",
        fail: "Falhou",
        unknown: "Sem resp."
      }[status] || (result.ok ? "OK" : "Falhou");
      tr.innerHTML = `
        <td>${result.sequence}</td>
        <td><span class="badge ${statusClass}">${statusLabel}</span></td>
        <td>${ms(result.latency_ms)}</td>
        <td>${ms(result.jitter_ms)}</td>
        <td>${escapeHtml(endpointText(result))}</td>
        <td>${escapeHtml(result.message)}</td>
        <td>${new Date(result.timestamp * 1000).toLocaleTimeString()}</td>
      `;
      rows.appendChild(tr);
      while (rows.children.length > MAX_TABLE_ROWS) {
        rows.removeChild(rows.firstElementChild);
      }
    }

    function resetOutput() {
      stats = { sent: 0, success: 0, latencySum: 0, minLatency: null, maxLatency: null, lastLatency: null, jitterSum: 0, jitterSamples: 0 };
      rows.innerHTML = "";
      consoleEl.textContent = "";
      updateSummary();
    }

    function closeSource() {
      if (source) {
        source.close();
        source = null;
      }
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }

    continuousInput.addEventListener("change", () => {
      updateProtocolFields();
    });

    modeInputs.forEach((input) => {
      input.addEventListener("change", updateProtocolFields);
    });
    protocolInputs.forEach((input) => {
      input.addEventListener("change", updateProtocolFields);
    });
    updateProtocolFields();

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      closeSource();
      resetOutput();

      const params = new URLSearchParams(new FormData(form));
      const mode = selectedMode();
      if (mode === "scan") {
        params.set("host", document.querySelector("#host").value);
        params.set("ports", scanPortsInput.value);
        params.set("concurrency", scanConcurrencyInput.value);
        if (showClosedInput.checked) {
          params.set("show_closed", "1");
        }
        appendLine(`Port Scan TCP ${params.get("host")} portas ${params.get("ports")}`, "info");
        setStatus("running", "Scaneando");
        startBtn.disabled = true;
        stopBtn.disabled = false;
        updateScanSummary({ tested: 0, open: 0, closed: 0, progress_percent: 0, avg_ms: null });
        source = new EventSource(`/api/scan-stream?${params.toString()}`);

        source.addEventListener("scan_result", (event) => {
          const result = JSON.parse(event.data);
          stats.sent += 1;
          if (result.ok) {
            stats.success += 1;
            stats.latencySum += result.latency_ms || 0;
            appendLine(`${result.port}: aberta em ${ms(result.latency_ms)} (${result.peer || result.host})`, "ok");
            addRow({
              sequence: result.port,
              ok: true,
              status: "ok",
              latency_ms: result.latency_ms,
              jitter_ms: null,
              peer: result.peer,
              host: result.host,
              message: "porta aberta",
              timestamp: result.timestamp,
            });
          } else if (showClosedInput.checked) {
            addRow({
              sequence: result.port,
              ok: false,
              status: "fail",
              latency_ms: null,
              jitter_ms: null,
              peer: null,
              host: result.host,
              message: result.message,
              timestamp: result.timestamp,
            });
          }
          updateScanSummary(result.summary);
        });

        source.addEventListener("scan_summary", (event) => {
          const summary = JSON.parse(event.data);
          updateScanSummary(summary);
          appendScanSummary("Resumo scan", summary);
          setStatus(summary.open > 0 ? "ok" : "fail", "Concluido");
          closeSource();
        });

        source.addEventListener("error", () => {
          if (!source) {
            return;
          }
          appendLine("Conexao com o servidor encerrada ou indisponivel.", "fail");
          setStatus("fail", "Erro");
          closeSource();
        });
        return;
      }

      const isContinuous = continuousInput.checked;
      if (isContinuous) {
        params.set("continuous", "1");
      }
      const protocol = selectedProtocol();
      params.set("protocol", protocol);
      const target = protocol === "icmp" ? params.get("host") : `${params.get("host")}:${params.get("port")}`;
      appendLine(isContinuous ? `${protocolLabel(protocol)} ${target} continuamente (-t)` : `${protocolLabel(protocol)} ${target} com ${params.get("count")} tentativa(s)`, "info");
      setStatus("running", isContinuous ? "Rodando" : "Testando");
      startBtn.disabled = true;
      stopBtn.disabled = false;

      source = new EventSource(`/api/stream?${params.toString()}`);

      source.addEventListener("probe", (event) => {
        const result = JSON.parse(event.data);
        stats.sent += 1;
        if (result.ok) {
          stats.success += 1;
          if (result.jitter_ms == null && stats.lastLatency != null) {
            result.jitter_ms = Math.abs(result.latency_ms - stats.lastLatency);
          }
          if (result.jitter_ms != null) {
            stats.jitterSum += result.jitter_ms;
            stats.jitterSamples += 1;
          }
          stats.lastLatency = result.latency_ms;
          stats.latencySum += result.latency_ms;
          stats.minLatency = stats.minLatency == null ? result.latency_ms : Math.min(stats.minLatency, result.latency_ms);
          stats.maxLatency = stats.maxLatency == null ? result.latency_ms : Math.max(stats.maxLatency, result.latency_ms);
          appendLine(`${result.sequence}: ${result.message} em ${ms(result.latency_ms)} (${result.peer || result.host})`, "ok");
        } else if (result.status === "unknown") {
          appendLine(`${result.sequence}: ${result.message}`, "info");
        } else {
          appendLine(`${result.sequence}: falhou - ${result.message}`, "fail");
        }
        addRow(result);
        updateSummary();
      });

      source.addEventListener("summary", (event) => {
        const summary = JSON.parse(event.data);
        updateSummary(summary);
        appendSummary("Resumo", summary);
        setStatus(summary.success > 0 ? "ok" : "fail", "Concluido");
        closeSource();
      });

      source.addEventListener("error", () => {
        if (!source) {
          return;
        }
        appendLine("Conexao com o servidor encerrada ou indisponivel.", "fail");
        setStatus("fail", "Erro");
        closeSource();
      });
    });

    stopBtn.addEventListener("click", () => {
      closeSource();
      setStatus("", "Interrompido");
      appendLine("Teste interrompido pelo usuario.", "info");
      appendSummary("Resumo parcial");
    });
  </script>
</body>
</html>
"""


@dataclass(frozen=True)
class ProbeConfig:
    protocol: str
    host: str
    port: int
    count: int
    timeout: float
    interval: float
    continuous: bool


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def parse_int(value: str | None, default: int, min_value: int, max_value: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"valor inteiro invalido: {value}") from exc
    if not min_value <= parsed <= max_value:
        raise ValueError(f"valor fora do intervalo {min_value}-{max_value}: {parsed}")
    return parsed


def parse_float(value: str | None, default: float, min_value: float, max_value: float) -> float:
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"valor numerico invalido: {value}") from exc
    if not min_value <= parsed <= max_value:
        raise ValueError(f"valor fora do intervalo {min_value}-{max_value}: {parsed:g}")
    return parsed


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on", "sim"}


def parse_protocol(value: str | None) -> str:
    protocol = (value or DEFAULT_PROTOCOL).strip().lower()
    if protocol not in {"tcp", "udp", "icmp"}:
        raise ValueError(f"protocolo invalido: {protocol}")
    return protocol


def first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0].strip()


def clean_host(raw_host: str | None) -> str:
    host = (raw_host or DEFAULT_HOST).strip()
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or ""
    host = host.strip().strip("[]")
    if not host:
        raise ValueError("host vazio")
    if any(char.isspace() for char in host):
        raise ValueError("host nao pode conter espacos")
    return host


def parse_config(query: dict[str, list[str]]) -> ProbeConfig:
    continuous = parse_bool(first_query_value(query, "continuous"))
    protocol = parse_protocol(first_query_value(query, "protocol"))
    return ProbeConfig(
        protocol=protocol,
        host=clean_host(first_query_value(query, "host")),
        port=parse_int(first_query_value(query, "port"), DEFAULT_PORT, 1, 65535),
        count=parse_int(first_query_value(query, "count"), DEFAULT_COUNT, 1, MAX_COUNT),
        timeout=parse_float(first_query_value(query, "timeout"), DEFAULT_TIMEOUT, MIN_TIMEOUT, MAX_TIMEOUT),
        interval=parse_float(first_query_value(query, "interval"), DEFAULT_INTERVAL, MIN_INTERVAL, MAX_INTERVAL),
        continuous=continuous,
    )


def format_sockaddr(sockaddr: tuple[Any, ...]) -> str:
    address = str(sockaddr[0])
    port = sockaddr[1]
    if ":" in address:
        return f"[{address}]:{port}"
    return f"{address}:{port}"


def format_socket_error(exc: BaseException, timeout: float) -> str:
    if isinstance(exc, socket.timeout):
        return f"timeout apos {timeout:g}s"

    message = str(exc)
    if isinstance(exc, OSError):
        message = exc.strerror or message
        winerror = getattr(exc, "winerror", None)
        if winerror == 10013:
            return "acesso negado pelo Windows/firewall ao abrir socket (WinError 10013)"
        if winerror:
            return f"{message} (WinError {winerror})"
    return message


def resolve_tcp_targets(host: str, port: int) -> list[tuple[int, int, int, tuple[Any, ...]]]:
    targets = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    unique_targets: list[tuple[int, int, int, tuple[Any, ...]]] = []
    seen: set[tuple[int, tuple[Any, ...]]] = set()
    for family, socktype, proto, _canonname, sockaddr in targets:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        unique_targets.append((family, socktype, proto, sockaddr))
    return unique_targets


def resolve_udp_targets(host: str, port: int) -> list[tuple[int, int, int, tuple[Any, ...]]]:
    targets = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
    unique_targets: list[tuple[int, int, int, tuple[Any, ...]]] = []
    seen: set[tuple[int, tuple[Any, ...]]] = set()
    for family, socktype, proto, _canonname, sockaddr in targets:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        unique_targets.append((family, socktype, proto, sockaddr))
    return unique_targets


def failed_probe(
    host: str,
    port: int,
    sequence: int,
    started: float,
    timestamp: float,
    message: str,
    attempts: list[dict[str, Any]] | None = None,
    status: str = "fail",
) -> dict[str, Any]:
    latency_ms = (time.perf_counter() - started) * 1000
    return {
        "sequence": sequence,
        "host": host,
        "port": port,
        "ok": False,
        "status": status,
        "latency_ms": None,
        "jitter_ms": None,
        "elapsed_ms": round(latency_ms, 3),
        "peer": None,
        "message": message,
        "attempts": attempts or [],
        "timestamp": timestamp,
    }


def tcp_probe(host: str, port: int, timeout: float, sequence: int) -> dict[str, Any]:
    started = time.perf_counter()
    timestamp = time.time()
    attempts: list[dict[str, Any]] = []

    try:
        targets = resolve_tcp_targets(host, port)
    except socket.gaierror as exc:
        return failed_probe(host, port, sequence, started, timestamp, f"falha DNS: {exc}")

    if not targets:
        return failed_probe(host, port, sequence, started, timestamp, "nenhum endereco TCP encontrado no DNS")

    for family, socktype, proto, sockaddr in targets:
        address = format_sockaddr(sockaddr)
        attempt_started = time.perf_counter()
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
                attempt_ms = (time.perf_counter() - attempt_started) * 1000
                peer = format_sockaddr(sock.getpeername())
                attempts.append({"address": address, "ok": True, "elapsed_ms": round(attempt_ms, 3)})
                return {
                    "sequence": sequence,
                    "host": host,
                    "port": port,
                    "ok": True,
                    "status": "ok",
                    "latency_ms": round(attempt_ms, 3),
                    "jitter_ms": None,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "peer": peer,
                    "message": "conectado",
                    "attempts": attempts,
                    "timestamp": timestamp,
                }
        except OSError as exc:
            attempt_ms = (time.perf_counter() - attempt_started) * 1000
            attempts.append(
                {
                    "address": address,
                    "ok": False,
                    "elapsed_ms": round(attempt_ms, 3),
                    "message": format_socket_error(exc, timeout),
                }
            )

    attempted = "; ".join(f"{item['address']} -> {item.get('message', 'falhou')}" for item in attempts)
    return failed_probe(host, port, sequence, started, timestamp, f"todos os enderecos falharam: {attempted}", attempts)


def udp_probe(host: str, port: int, timeout: float, sequence: int) -> dict[str, Any]:
    started = time.perf_counter()
    timestamp = time.time()
    attempts: list[dict[str, Any]] = []
    payload = b"network-probe"

    try:
        targets = resolve_udp_targets(host, port)
    except socket.gaierror as exc:
        return failed_probe(host, port, sequence, started, timestamp, f"falha DNS: {exc}")

    if not targets:
        return failed_probe(host, port, sequence, started, timestamp, "nenhum endereco UDP encontrado no DNS")

    for family, socktype, proto, sockaddr in targets:
        address = format_sockaddr(sockaddr)
        attempt_started = time.perf_counter()
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
                sock.send(payload)
                try:
                    data = sock.recv(4096)
                    attempt_ms = (time.perf_counter() - attempt_started) * 1000
                    peer = format_sockaddr(sock.getpeername())
                    attempts.append(
                        {
                            "address": address,
                            "ok": True,
                            "elapsed_ms": round(attempt_ms, 3),
                            "bytes": len(data),
                        }
                    )
                    return {
                        "sequence": sequence,
                        "host": host,
                        "port": port,
                        "ok": True,
                        "status": "ok",
                        "latency_ms": round(attempt_ms, 3),
                        "jitter_ms": None,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                        "peer": peer,
                        "message": f"resposta UDP ({len(data)} bytes)",
                        "attempts": attempts,
                        "timestamp": timestamp,
                    }
                except socket.timeout:
                    attempt_ms = (time.perf_counter() - attempt_started) * 1000
                    message = "sem resposta UDP; porta pode estar aberta/silenciosa ou filtrada"
                    attempts.append({"address": address, "ok": False, "status": "unknown", "elapsed_ms": round(attempt_ms, 3), "message": message})
                except OSError as exc:
                    attempt_ms = (time.perf_counter() - attempt_started) * 1000
                    message = format_socket_error(exc, timeout)
                    if getattr(exc, "winerror", None) == 10054:
                        message = "porta UDP recusada por ICMP port unreachable (WinError 10054)"
                    attempts.append({"address": address, "ok": False, "elapsed_ms": round(attempt_ms, 3), "message": message})
        except OSError as exc:
            attempt_ms = (time.perf_counter() - attempt_started) * 1000
            attempts.append(
                {
                    "address": address,
                    "ok": False,
                    "elapsed_ms": round(attempt_ms, 3),
                    "message": format_socket_error(exc, timeout),
                }
            )

    attempted = "; ".join(f"{item['address']} -> {item.get('message', 'falhou')}" for item in attempts)
    if any(item.get("status") == "unknown" for item in attempts):
        return failed_probe(host, port, sequence, started, timestamp, f"sem resposta UDP: {attempted}", attempts, status="unknown")
    return failed_probe(host, port, sequence, started, timestamp, f"todos os enderecos UDP falharam: {attempted}", attempts)


def parse_ping_latency(output: str, elapsed_ms: float) -> float | None:
    match = re.search(r"(?:tempo|time)\s*([=<])\s*([0-9]+(?:[,.][0-9]+)?)\s*ms", output, re.IGNORECASE)
    if not match:
        return round(elapsed_ms, 3) if "ttl=" in output.lower() else None

    comparator = match.group(1)
    value = float(match.group(2).replace(",", "."))
    if comparator == "<":
        return min(value, 0.5)
    return value


def parse_ping_peer(output: str, host: str) -> str:
    match = re.search(r"\[([0-9a-fA-F:.]+)\]", output)
    return match.group(1) if match else host


def ping_message(output: str) -> str:
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if any(token in lowered for token in ("esgotado", "timed out", "inacess", "unreachable", "falha", "could not find", "nao encontrou", "não encontrou")):
            return text
    return "sem resposta ICMP"


def icmp_probe(host: str, timeout: float, sequence: int) -> dict[str, Any]:
    started = time.perf_counter()
    timestamp = time.time()
    timeout_ms = max(1, int(timeout * 1000))
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        command = ["ping", "-c", "1", "-W", str(max(1, int(round(timeout)))), host]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 2,
        )
    except FileNotFoundError:
        return failed_probe(host, 0, sequence, started, timestamp, "comando ping nao encontrado")
    except subprocess.TimeoutExpired:
        return failed_probe(host, 0, sequence, started, timestamp, f"timeout ICMP apos {timeout:g}s")

    elapsed_ms = (time.perf_counter() - started) * 1000
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    latency_ms = parse_ping_latency(output, elapsed_ms)
    if completed.returncode == 0 and latency_ms is not None:
        return {
            "sequence": sequence,
            "host": host,
            "port": None,
            "ok": True,
            "status": "ok",
            "latency_ms": round(latency_ms, 3),
            "jitter_ms": None,
            "elapsed_ms": round(elapsed_ms, 3),
            "peer": parse_ping_peer(output, host),
            "message": "resposta ICMP",
            "attempts": [],
            "timestamp": timestamp,
        }

    return failed_probe(host, 0, sequence, started, timestamp, ping_message(output))


def run_probe_once(config: ProbeConfig, sequence: int) -> dict[str, Any]:
    if config.protocol == "tcp":
        return tcp_probe(config.host, config.port, config.timeout, sequence)
    if config.protocol == "udp":
        return udp_probe(config.host, config.port, config.timeout, sequence)
    return icmp_probe(config.host, config.timeout, sequence)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    sent = len(results)
    successful = [item["latency_ms"] for item in results if item.get("ok") and item.get("latency_ms") is not None]
    success = len(successful)
    failed = sent - success
    jitter_values = [abs(current - previous) for previous, current in zip(successful, successful[1:])]

    return {
        "sent": sent,
        "success": success,
        "failed": failed,
        "loss_percent": round((failed / sent * 100) if sent else 0.0, 3),
        "min_ms": round(min(successful), 3) if successful else None,
        "avg_ms": round(sum(successful) / success, 3) if successful else None,
        "max_ms": round(max(successful), 3) if successful else None,
        "jitter_ms": round(sum(jitter_values) / len(jitter_values), 3) if jitter_values else None,
    }


def run_tcping(config: ProbeConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    last_latency = None
    for sequence in range(1, config.count + 1):
        result = run_probe_once(config, sequence)
        last_latency = apply_jitter(result, last_latency)
        results.append(result)
        if sequence < config.count and config.interval > 0:
            time.sleep(config.interval)
    return results, summarize(results)


def parse_ports(raw_ports: str | None) -> list[int]:
    text = (raw_ports or "").strip()
    if not text:
        raise ValueError("informe uma lista ou faixa de portas para scan")

    ports: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            pieces = part.split("-", 1)
            if len(pieces) != 2 or not pieces[0] or not pieces[1]:
                raise ValueError(f"faixa de portas invalida: {part}")
            start = int(pieces[0])
            end = int(pieces[1])
            if start > end:
                raise ValueError(f"faixa de portas invertida: {part}")
            if start < 1 or end > 65535:
                raise ValueError(f"porta fora do intervalo 1-65535: {part}")
            ports.update(range(start, end + 1))
        else:
            port = int(part)
            if not 1 <= port <= 65535:
                raise ValueError(f"porta fora do intervalo 1-65535: {port}")
            ports.add(port)

        if len(ports) > MAX_SCAN_PORTS:
            raise ValueError(f"scan limitado a {MAX_SCAN_PORTS} portas por execucao")

    if not ports:
        raise ValueError("nenhuma porta valida para scan")
    return sorted(ports)


def parse_scan_concurrency(value: str | None) -> int:
    concurrency = parse_int(value, 100, 1, MAX_SCAN_CONCURRENCY)
    return min(concurrency, MAX_SCAN_CONCURRENCY)


def scan_summary(results: list[dict[str, Any]], total: int) -> dict[str, Any]:
    tested = len(results)
    open_results = [item for item in results if item.get("ok")]
    latencies = [item["latency_ms"] for item in open_results if item.get("latency_ms") is not None]
    return {
        "total": total,
        "tested": tested,
        "open": len(open_results),
        "closed": tested - len(open_results),
        "remaining": max(total - tested, 0),
        "progress_percent": round((tested / total * 100) if total else 0.0, 3),
        "min_ms": round(min(latencies), 3) if latencies else None,
        "avg_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "max_ms": round(max(latencies), 3) if latencies else None,
    }


def scan_tcp_port(host: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    timestamp = time.time()
    attempts: list[dict[str, Any]] = []

    try:
        targets = resolve_tcp_targets(host, port)
    except socket.gaierror as exc:
        return {
            "host": host,
            "port": port,
            "ok": False,
            "status": "fail",
            "latency_ms": None,
            "peer": None,
            "message": f"falha DNS: {exc}",
            "attempts": attempts,
            "timestamp": timestamp,
        }

    for family, socktype, proto, sockaddr in targets:
        address = format_sockaddr(sockaddr)
        attempt_started = time.perf_counter()
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
                latency_ms = (time.perf_counter() - started) * 1000
                attempts.append({"address": address, "ok": True, "elapsed_ms": round((time.perf_counter() - attempt_started) * 1000, 3)})
                return {
                    "host": host,
                    "port": port,
                    "ok": True,
                    "status": "ok",
                    "latency_ms": round(latency_ms, 3),
                    "peer": format_sockaddr(sock.getpeername()),
                    "message": "porta aberta",
                    "attempts": attempts,
                    "timestamp": timestamp,
                }
        except OSError as exc:
            attempts.append(
                {
                    "address": address,
                    "ok": False,
                    "elapsed_ms": round((time.perf_counter() - attempt_started) * 1000, 3),
                    "message": format_socket_error(exc, timeout),
                }
            )

    message = "fechada ou filtrada"
    if attempts:
        last_message = attempts[-1].get("message")
        if last_message:
            message = last_message
    return {
        "host": host,
        "port": port,
        "ok": False,
        "status": "fail",
        "latency_ms": None,
        "peer": None,
        "message": message,
        "attempts": attempts,
        "timestamp": timestamp,
    }


def run_port_scan(host: str, ports: list[int], timeout: float, concurrency: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    max_workers = min(concurrency, len(ports))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scan_tcp_port, host, port, timeout) for port in ports]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["port"])
    return results, scan_summary(results, len(ports))


def apply_jitter(result: dict[str, Any], last_latency: float | None) -> float | None:
    if not result.get("ok") or result.get("latency_ms") is None:
        result["jitter_ms"] = None
        return last_latency

    latency = float(result["latency_ms"])
    result["jitter_ms"] = round(abs(latency - last_latency), 3) if last_latency is not None else None
    return latency


class TcpingHandler(BaseHTTPRequestHandler):
    server_version = "TcpingWeb/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        if getattr(self.server, "quiet", False):
            return
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(INDEX_HTML)
            return
        if parsed.path in {"/api/tcping", "/api/probe"}:
            self.handle_tcping(parsed.query)
            return
        if parsed.path == "/api/stream":
            self.handle_stream(parsed.query)
            return
        if parsed.path == "/api/scan":
            self.handle_scan(parsed.query)
            return
        if parsed.path == "/api/scan-stream":
            self.handle_scan_stream(parsed.query)
            return
        if parsed.path == "/health":
            self.send_json({"ok": True})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "rota nao encontrada")

    def parse_request_config(self, raw_query: str) -> ProbeConfig:
        query = parse_qs(raw_query, keep_blank_values=True)
        return parse_config(query)

    def handle_tcping(self, raw_query: str) -> None:
        try:
            config = self.parse_request_config(raw_query)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        results, summary = run_tcping(config)
        self.send_json(
            {
                "target": {
                    "protocol": config.protocol,
                    "host": config.host,
                    "port": None if config.protocol == "icmp" else config.port,
                    "count": config.count,
                    "timeout": config.timeout,
                    "interval": config.interval,
                    "continuous": config.continuous,
                },
                "results": results,
                "summary": summary,
            }
        )

    def parse_scan_request(self, raw_query: str) -> tuple[str, list[int], float, int, bool]:
        query = parse_qs(raw_query, keep_blank_values=True)
        host = clean_host(first_query_value(query, "host"))
        ports = parse_ports(first_query_value(query, "ports") or first_query_value(query, "scan_ports"))
        timeout = parse_float(first_query_value(query, "timeout"), DEFAULT_TIMEOUT, MIN_TIMEOUT, MAX_TIMEOUT)
        concurrency = parse_scan_concurrency(first_query_value(query, "concurrency") or first_query_value(query, "scan_concurrency"))
        show_closed = parse_bool(first_query_value(query, "show_closed"))
        return host, ports, timeout, concurrency, show_closed

    def handle_scan(self, raw_query: str) -> None:
        try:
            host, ports, timeout, concurrency, _show_closed = self.parse_scan_request(raw_query)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        results, summary = run_port_scan(host, ports, timeout, concurrency)
        self.send_json(
            {
                "target": {
                    "protocol": "tcp",
                    "host": host,
                    "ports": ports,
                    "timeout": timeout,
                    "concurrency": concurrency,
                },
                "results": results,
                "summary": summary,
            }
        )

    def handle_stream(self, raw_query: str) -> None:
        try:
            config = self.parse_request_config(raw_query)
        except ValueError as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            self.send_event("error", {"error": str(exc)})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()

        results = []
        sequence = 1
        last_latency = None
        while config.continuous or sequence <= config.count:
            result = run_probe_once(config, sequence)
            last_latency = apply_jitter(result, last_latency)
            results.append(result)
            if not self.send_event("probe", result):
                return
            if (config.continuous or sequence < config.count) and config.interval > 0:
                time.sleep(config.interval)
            sequence += 1

        if not config.continuous:
            self.send_event("summary", summarize(results))

    def handle_scan_stream(self, raw_query: str) -> None:
        try:
            host, ports, timeout, concurrency, show_closed = self.parse_scan_request(raw_query)
        except ValueError as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            self.send_event("error", {"error": str(exc)})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()

        results: list[dict[str, Any]] = []
        executor = ThreadPoolExecutor(max_workers=min(concurrency, len(ports)))
        futures = [executor.submit(scan_tcp_port, host, port, timeout) for port in ports]
        try:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                result["summary"] = scan_summary(results, len(ports))
                should_send = result.get("ok") or show_closed
                if should_send and not self.send_event("scan_result", result):
                    for pending in futures:
                        pending.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                if not should_send:
                    progress_event = {
                        "host": host,
                        "port": result["port"],
                        "ok": False,
                        "status": "progress",
                        "latency_ms": None,
                        "peer": None,
                        "message": result["message"],
                        "timestamp": result["timestamp"],
                        "summary": result["summary"],
                    }
                    if not self.send_event("scan_result", progress_event):
                        for pending in futures:
                            pending.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        return
            summary = scan_summary(results, len(ports))
            open_results = sorted([item for item in results if item.get("ok")], key=lambda item: item["port"])
            if not self.send_event("scan_summary", {**summary, "open_ports": [item["port"] for item in open_results]}):
                return
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_event(self, event: str, data: dict[str, Any]) -> bool:
        payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
        try:
            self.wfile.write(payload)
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            return False


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aplicacao web para testar TCP, UDP e ICMP.")
    parser.add_argument("--host", default="127.0.0.1", help="interface do servidor web")
    parser.add_argument("--port", type=int, default=8081, help="porta do servidor web")
    parser.add_argument("--quiet", action="store_true", help="nao escreve logs no console")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    address = (args.host, args.port)
    server = ThreadingHTTPServer(address, TcpingHandler)
    server.quiet = args.quiet  # type: ignore[attr-defined]
    if not args.quiet:
        print(f"Network Probe em http://{args.host}:{args.port}")
        print("Pressione Ctrl+C para parar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nEncerrando...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
