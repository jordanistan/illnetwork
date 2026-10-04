'use strict';
// No networking, storage, HTML injection, trackers, or third-party scripts.
const walk = document.querySelector('[data-walk-calculator]');
if (walk) {
  const update = () => {
    const duration = walk.querySelector('#walk-duration').value;
    const count = Number(walk.querySelector('#walk-count').value);
    const each = duration === '60' ? 35 : 22;
    walk.querySelector('[data-total]').textContent = `$${(each * count).toFixed(0)} / week`;
    walk.querySelector('[data-estimate]').textContent = `${count} × ${duration}-minute walks at $${each} per walk. Planning estimate only; no package discount or booking implied.`;
  };
  walk.addEventListener('change', update);
  update();
}
const filters = document.querySelector('[data-filters]');
if (filters) {
  filters.addEventListener('click', event => {
    const button = event.target.closest('button[data-filter]');
    if (!button) return;
    filters.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    let visible = 0;
    document.querySelectorAll('[data-category]').forEach(card => {
      const show = button.dataset.filter === 'all' || card.dataset.category === button.dataset.filter;
      card.hidden = !show;
      if (show) visible += 1;
    });
    document.querySelector('[data-filter-count]').textContent = `${visible} planning ${visible === 1 ? 'category' : 'categories'} shown. These are not venue listings.`;
  });
}
document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
const workflow = document.querySelector('[data-workflow]');
if (workflow) {
  const notes = {
    leads: 'Start with a lead intake checklist. Keep outreach drafts for human review; do not auto-send messages.',
    reports: 'Use approved sample evidence. Keep a human review before publishing or sharing a report.',
    scheduling: 'Start with availability suggestions. Confirm the appointment before making a calendar commitment.',
    bookkeeping: 'Suggest transaction categories. Reconcile against the original records and review before filing.'
  };
  const update = () => { workflow.querySelector('[data-workflow-output]').textContent = notes[workflow.querySelector('select').value]; };
  workflow.addEventListener('change', update); update();
}

// Plain text mirrors allow long notes to flow across printed pages.
document.querySelectorAll('.worksheet').forEach(worksheet => {
  const fields = [...worksheet.querySelectorAll('textarea')];
  const mirrors = fields.map(field => {
    const mirror = document.createElement('div');
    mirror.className = 'print-value';
    mirror.setAttribute('aria-hidden', 'true');
    field.after(mirror);
    return mirror;
  });
  const syncPrint = () => fields.forEach((field, i) => { mirrors[i].textContent = field.value; });
  worksheet.addEventListener('input', syncPrint);
  window.addEventListener('beforeprint', syncPrint);
  window.addEventListener('pageshow', syncPrint);
  worksheet.querySelector('[data-clear-worksheet]').addEventListener('click', () => {
    fields.forEach(field => { field.value = ''; });
    syncPrint();
    worksheet.querySelector('[data-clear-status]').textContent = 'Worksheet cleared.';
    fields[0].focus();
  });
  syncPrint();
});
