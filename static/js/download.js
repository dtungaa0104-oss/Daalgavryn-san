/* ═══════════════════════════════════════════════════════
   ОРХОНТУУЛ ЕБС — Татах / Хэвлэх хэрэгсэл
   ═══════════════════════════════════════════════════════ */

// ── Форматууд ──────────────────────────────────────────
function formatTXT(questions, title) {
  let t = `${'═'.repeat(60)}\n`;
  t += `   ОРХОНТУУЛ ЕБС\n`;
  t += `   ${title}\n`;
  t += `   Нийт: ${questions.length} даалгавар\n`;
  t += `${'═'.repeat(60)}\n\n`;
  questions.forEach((q, i) => {
    t += `${i+1}. `;
    if (q.level) t += `[${q.level}] `;
    if (q.bloom) t += `[${q.bloom}] `;
    if (q.topic) t += `(${q.topic}) `;
    t += `\n${q.question}\n`;
    if (q.options) q.options.forEach(o => t += `   ${o}\n`);
    t += `   Оноо: ${q.score}п`;
    if (q.answer) t += `  |  Зөв: ${q.answer}`;
    t += '\n\n';
  });
  t += `\n${'─'.repeat(60)}\nХАРИУЛТЫН ХУУДАС\n`;
  questions.forEach((q, i) => t += `${i+1}. ${q.answer||'—'}   `);
  return t;
}

function formatHTML(questions, title) {
  return `<!DOCTYPE html>
<html lang="mn"><head><meta charset="UTF-8">
<title>${title}</title>
<style>
  @page { margin: 20mm; }
  body { font-family: 'Times New Roman', serif; font-size: 12pt; color: #000; line-height: 1.6; }
  .header { text-align:center; border-bottom:2px solid #000; padding-bottom:10px; margin-bottom:20px; }
  .school  { font-size:14pt; font-weight:bold; }
  .title   { font-size:16pt; font-weight:bold; margin:8px 0; }
  .meta    { font-size:11pt; color:#444; }
  .question { margin-bottom:18px; page-break-inside:avoid; }
  .q-num   { font-weight:bold; }
  .q-text  { margin:4px 0 8px; }
  .options { display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-left:20px; }
  .opt     { padding:2px 0; }
  .q-meta  { font-size:10pt; color:#666; margin-top:4px; }
  .answer-sheet { margin-top:30px; border-top:2px solid #000; padding-top:12px; }
  .ans-grid { display:flex; flex-wrap:wrap; gap:12px; margin-top:8px; }
  .ans-item { font-size:11pt; }
  .badge   { display:inline-block; padding:1px 8px; border-radius:10px; font-size:10pt; font-weight:bold; margin-right:4px; }
  .b-mo    { background:#E8F5E9; color:#2E7D32; }
  .b-ch    { background:#E3F2FD; color:#1565C0; }
  .b-he    { background:#F3E5F5; color:#6A1B9A; }
  @media print { .no-print { display:none; } }
</style>
</head><body>
<div class="header">
  <div class="school">ОРХОНТУУЛ ЕБС</div>
  <div class="title">${title}</div>
  <div class="meta">Нийт: ${questions.length} даалгавар &nbsp;|&nbsp; Огноо: ${new Date().toLocaleDateString('mn-MN')}</div>
</div>

<button class="no-print" onclick="window.print()" style="margin-bottom:16px;padding:8px 20px;background:#0F6E56;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px">🖨 Хэвлэх</button>

${questions.map((q, i) => {
  const lvlClass = q.level==='Мэдлэг ойлголт'?'b-mo':q.level==='Чадвар'?'b-ch':'b-he';
  return `<div class="question">
  <div class="q-num">${i+1}.</div>
  <div class="q-text">${q.question}</div>
  ${q.options ? `<div class="options">${q.options.map(o=>`<div class="opt">${o}</div>`).join('')}</div>` : ''}
  <div class="q-meta">
    ${q.level?`<span class="badge ${lvlClass}">${q.level}</span>`:''}
    ${q.bloom?`<span style="font-size:10pt;color:#666">${q.bloom}</span>`:''}
    &nbsp; ${q.score}п
  </div>
</div>`;
}).join('')}

<div class="answer-sheet">
  <strong>ХАРИУЛТЫН ХУУДАС</strong>
  <div class="ans-grid">
    ${questions.map((q,i)=>`<span class="ans-item">${i+1}. <strong>${q.answer||'—'}</strong></span>`).join('')}
  </div>
</div>
</body></html>`;
}

// ── Татах функцүүд ──────────────────────────────────────
function downloadAsTXT(questions, title) {
  if (!questions.length) { alert('Даалгавар сонгоно уу'); return; }
  const blob = new Blob([formatTXT(questions, title)], {type:'text/plain;charset=utf-8'});
  triggerDownload(blob, `daalgavar_${Date.now()}.txt`);
}

function downloadAsHTML(questions, title) {
  if (!questions.length) { alert('Даалгавар сонгоно уу'); return; }
  const blob = new Blob([formatHTML(questions, title)], {type:'text/html;charset=utf-8'});
  triggerDownload(blob, `daalgavar_${Date.now()}.html`);
}

function printQuestions(questions, title) {
  if (!questions.length) { alert('Даалгавар сонгоно уу'); return; }
  const win = window.open('', '_blank');
  win.document.write(formatHTML(questions, title));
  win.document.close();
  setTimeout(() => win.print(), 600);
}

function triggerDownload(blob, filename) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ── Dropdown товч ──────────────────────────────────────
function showDownloadMenu(btnEl, getQuestions, getTitle) {
  // Одоо байгаа меню хаах
  document.querySelectorAll('.dl-menu').forEach(m => m.remove());

  const qs = getQuestions();
  if (!qs.length) { alert('Даалгавар сонгоно уу'); return; }

  const menu = document.createElement('div');
  menu.className = 'dl-menu';
  menu.innerHTML = `
    <div class="dl-item" onclick="downloadAsTXT(window._dlQs, window._dlTitle)">📄 .TXT татах</div>
    <div class="dl-item" onclick="downloadAsHTML(window._dlQs, window._dlTitle)">📋 .HTML татах</div>
    <div class="dl-item" onclick="printQuestions(window._dlQs, window._dlTitle)">🖨 Хэвлэх</div>
  `;

  window._dlQs    = qs;
  window._dlTitle = getTitle ? getTitle() : 'Орхонтуул ЕБС — Даалгавар';

  const rect = btnEl.getBoundingClientRect();
  menu.style.cssText = `position:fixed;top:${rect.bottom+4}px;left:${rect.left}px;z-index:9999`;
  document.body.appendChild(menu);

  setTimeout(() => document.addEventListener('click', () => menu.remove(), {once:true}), 10);
}
