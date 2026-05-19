const form        = document.getElementById('analyze-form');
const formCard    = document.getElementById('form-section');
const loadCard    = document.getElementById('loading-card');
const loadMsg     = document.getElementById('loading-msg');
const progressFill = document.getElementById('progress-fill');
const submitBtn   = document.getElementById('submit-btn');
const btnAdd      = document.getElementById('btn-add');
const addHint     = document.getElementById('add-hint');
const compList    = document.getElementById('competitors-list');

const MAX_COMPETITORS = 4;
let compCount = 1;

const PLACEHOLDERS = ['e.g. Adidas', 'e.g. Puma', 'e.g. Reebok', 'e.g. Under Armour'];

function updateUI() {
  btnAdd.disabled = compCount >= MAX_COMPETITORS;
  const remaining = MAX_COMPETITORS - compCount;
  addHint.innerHTML = compCount >= MAX_COMPETITORS
    ? 'Maximum of 4 competitors reached.'
    : `You can add up to <strong>${remaining} more</strong> competitor${remaining !== 1 ? 's' : ''}.`;
  const rows = compList.querySelectorAll('.competitor-row');
  rows.forEach(row => {
    const removeBtn = row.querySelector('.btn-remove-competitor');
    if (removeBtn) removeBtn.style.display = compCount > 1 ? 'block' : 'none';
  });
}

function fillCompetitor(name) {
  const inputs = compList.querySelectorAll('input[name="competitor"]');
  for (let input of inputs) {
    if (!input.value.trim()) {
      input.value = name;
      return;
    }
  }
  if (compCount < MAX_COMPETITORS) {
    btnAdd.click();
    setTimeout(() => {
      const newInputs = compList.querySelectorAll('input[name="competitor"]');
      newInputs[newInputs.length - 1].value = name;
    }, 50);
  } else {
    alert("You have reached the maximum of 4 competitors.");
  }
}

async function addCompetitor() {
  const input = document.getElementById('new-competitor-name');
  const name = input.value.trim();
  if (!name) return;
  
  try {
    const res = await fetch('/api/competitors/add/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ name })
    });
    const data = await res.json();
    if (data.id) {
      input.value = '';
      const list = document.getElementById('saved-competitors-list');
      const msg = document.getElementById('no-saved-msg');
      if (msg) msg.remove();
      
      const span = document.createElement('span');
      span.className = 'competitor-badge';
      span.dataset.id = data.id;
      span.style.cssText = 'background: var(--white); border: 1px solid var(--border); padding: 0.3rem 0.6rem; border-radius: 12px; font-size: 0.8rem; display: flex; align-items: center; gap: 0.4rem; cursor: pointer; transition: border-color .2s;';
      span.innerHTML = `
        <span onclick="fillCompetitor('${data.name}')" style="flex-grow: 1;">${data.name}</span>
        <button type="button" onclick="deleteCompetitor(${data.id})" style="background: none; border: none; color: var(--red); cursor: pointer; font-weight: bold; font-size: 1rem; line-height: 1;">&times;</button>
      `;
      list.appendChild(span);
    } else {
      alert(data.error || 'Failed to add');
    }
  } catch (err) {
    console.error(err);
  }
}

async function deleteCompetitor(id) {
  try {
    const res = await fetch(`/api/competitors/delete/${id}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    const data = await res.json();
    if (data.success) {
      const el = document.querySelector(`.competitor-badge[data-id="${id}"]`);
      if (el) el.remove();
    } else {
      alert(data.error || 'Failed to delete');
    }
  } catch (err) {
    console.error(err);
  }
}

btnAdd.addEventListener('click', () => {
  if (compCount >= MAX_COMPETITORS) return;
  compCount++;
  const idx = compCount;

  const row = document.createElement('div');
  row.className = 'competitor-row';
  row.id = `comp-row-${idx}`;
  row.innerHTML = `
    <div class="field-group">
      <label for="comp-${idx}">Competitor ${idx}</label>
      <input type="text" id="comp-${idx}" name="competitor"
             placeholder="${PLACEHOLDERS[idx - 1] || 'e.g. Competitor name'}"
             autocomplete="off"/>
    </div>
    <button type="button" class="btn-remove-competitor" data-row="${idx}" aria-label="Remove competitor ${idx}">
      Remove
    </button>
  `;
  row.style.opacity = '0';
  row.style.transform = 'translateY(-8px)';
  compList.appendChild(row);
  requestAnimationFrame(() => {
    row.style.transition = 'opacity .25s, transform .25s';
    row.style.opacity = '1';
    row.style.transform = 'translateY(0)';
  });

  row.querySelector('.btn-remove-competitor').addEventListener('click', () => removeRow(idx));
  row.querySelector('input').focus();
  updateUI();
});

function removeRow(idx) {
  const row = document.getElementById(`comp-row-${idx}`);
  if (!row) return;
  row.style.transition = 'opacity .2s, transform .2s';
  row.style.opacity = '0';
  row.style.transform = 'translateY(-6px)';
  setTimeout(() => {
    row.remove();
    compCount--;
    const rows = compList.querySelectorAll('.competitor-row');
    rows.forEach((r, i) => {
      const num = i + 1;
      r.id = `comp-row-${num}`;
      const label = r.querySelector('label');
      const input = r.querySelector('input');
      const removeBtn = r.querySelector('.btn-remove-competitor');
      if (label) label.textContent = `Competitor ${num}${num === 1 ? ' *' : ''}`;
      if (input) {
        input.id = `comp-${num}`;
        input.placeholder = PLACEHOLDERS[num - 1] || 'e.g. Competitor name';
      }
      if (removeBtn) removeBtn.dataset.row = num;
    });
    updateUI();
  }, 200);
}

updateUI();

const STEPS = ['step-1', 'step-2', 'step-3', 'step-4'];
const STEP_MSGS = [
  'Searching for official YouTube channels…',
  'Fetching recent video data for all companies…',
  'Computing analytics and engagement metrics…',
  'Generating your professional PowerPoint report…',
];

let pollInterval = null;
let stepIndex = 0;
let advanceTimer = null;

function advanceStep() {
  if (stepIndex > 0) {
    const prev = document.getElementById(STEPS[stepIndex - 1]);
    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
  }
  if (stepIndex < STEPS.length) {
    const curr = document.getElementById(STEPS[stepIndex]);
    if (curr) curr.classList.add('active');
    loadMsg.textContent = STEP_MSGS[stepIndex];
    progressFill.style.width = (10 + stepIndex * 22) + '%';
    stepIndex++;
  }
}

function getCookie(name) {
  let val = null;
  document.cookie.split(';').forEach(c => {
    c = c.trim();
    if (c.startsWith(name + '=')) val = decodeURIComponent(c.slice(name.length + 1));
  });
  return val;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const own = document.getElementById('own_company').value.trim();
  if (!own) {
    document.getElementById('own_company').focus();
    showFieldError('own_company', 'Please enter your company name.');
    return;
  }

  const competitorInputs = compList.querySelectorAll('input[name="competitor"]');
  const competitors = Array.from(competitorInputs).map(i => i.value.trim()).filter(Boolean);

  if (competitors.length === 0) {
    showFieldError('comp-1', 'Please enter at least one competitor name.');
    return;
  }

  let reportName = document.getElementById('report_name').value.trim();
  if (!reportName) {
    const d = new Date();
    const pad = (n) => n.toString().padStart(2, '0');
    reportName = `comp-${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  submitBtn.disabled = true;
  formCard.classList.add('hidden');
  loadCard.classList.remove('hidden');
  stepIndex = 0;
  progressFill.style.width = '5%';
  advanceStep();
  advanceTimer = setInterval(advanceStep, 12000);

  try {
    const res = await fetch('/api/analyze/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ own_company: own, competitors, report_name: reportName }),
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      clearInterval(advanceTimer);
      showError(data.error || 'Server error. Please try again.');
      return;
    }

    pollInterval = setInterval(() => pollStatus(data.report_id), 4000);
  } catch (err) {
    clearInterval(advanceTimer);
    showError('Network error: ' + err.message);
  }
});

async function pollStatus(reportId) {
  try {
    const res = await fetch(`/api/status/${reportId}/`);
    const data = await res.json();
    if (data.status === 'done') {
      clearInterval(pollInterval);
      clearInterval(advanceTimer);
      progressFill.style.width = '100%';
      loadMsg.textContent = 'Report ready. Redirecting…';
      setTimeout(() => { window.location.href = data.redirect_url; }, 700);
    } else if (data.status === 'error') {
      clearInterval(pollInterval);
      clearInterval(advanceTimer);
      showError(data.error || 'Analysis failed. Please try again.');
    }
  } catch (err) {
    console.error('Poll error:', err);
  }
}

function showFieldError(fieldId, msg) {
  const el = document.getElementById(fieldId);
  if (el) {
    el.style.borderColor = 'var(--red)';
    el.focus();
    setTimeout(() => { el.style.borderColor = ''; }, 3000);
  }
  const existing = document.getElementById('field-err-msg');
  if (existing) existing.remove();
  const errEl = document.createElement('p');
  errEl.id = 'field-err-msg';
  errEl.style.cssText = 'color:#ff4d6d;font-size:.78rem;margin-top:.4rem;';
  errEl.textContent = msg;
  if (el) el.parentElement.appendChild(errEl);
  setTimeout(() => errEl.remove(), 4000);
}

function showError(msg) {
  clearInterval(pollInterval);
  loadCard.classList.add('hidden');
  formCard.classList.remove('hidden');
  submitBtn.disabled = false;
  const existing = document.getElementById('global-err');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.id = 'global-err';
  el.style.cssText = 'background:rgba(255,77,109,.1);border:1px solid rgba(255,77,109,.4);color:#ff4d6d;padding:.75rem 1rem;border-radius:8px;font-size:.88rem;margin-bottom:1rem;';
  el.textContent = msg;
  form.insertBefore(el, form.firstChild);
  setTimeout(() => el.remove(), 6000);
}
