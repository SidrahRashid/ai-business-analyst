/**
 * CAMELLIA TEA ATELIER & ANALYTICS PORTAL
 */

// Application State
const state = {
  token: localStorage.getItem('camellia_token') || null,
  client: null,
  charts: {
    trend: null,
    donut: null,
    ranking: null,
    channel: null
  },
  filters: {
    year: ['All'],
    month: ['All'],
    category: ['All'],
    secondary: ['All'],
    tertiary: ['All']
  },
  rawRecords: [],
  curatedRecords: [],
  chatHistory: [],
  conversationContext: {},
  lastKpiData: null,
  lastMatrixData: null,
  lastBriefingData: null,
  activeTab: 'chat'
};

// Tea Color Palette for Chart.js
const TEA_PALETTE = {
  forest: '#1b4332',
  leaf: '#2d6a4f',
  matcha: '#40916c',
  sage: '#52b788',
  amber: '#c58f3b',
  copper: '#bc6c25',
  golden: '#dda15e',
  terracotta: '#b2533e',
  mist: '#d8f3dc',
  colors: ['#2d6a4f', '#c58f3b', '#40916c', '#bc6c25', '#52b788', '#dda15e', '#b2533e', '#1b4332']
};

// Indian Numbering and Currency Formatters
function formatIndianNumber(val, decimals = 3) {
  if (val === null || val === undefined || isNaN(val)) return '0.' + '0'.repeat(decimals);
  const num = Number(val);
  const fixed = Math.abs(num).toFixed(decimals);
  const parts = fixed.split('.');
  let intPart = parts[0];
  const decPart = parts.length > 1 ? '.' + parts[1] : '';

  if (intPart.length > 3) {
    const lastThree = intPart.substring(intPart.length - 3);
    const remaining = intPart.substring(0, intPart.length - 3);
    const grouped = remaining.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    intPart = grouped + ',' + lastThree;
  }
  return (num < 0 ? '-' : '') + intPart + decPart;
}

function formatIndianCurrency(val) {
  if (val === null || val === undefined || isNaN(val)) return 'Rs. 0.00';
  const num = Number(val);
  const abs = Math.abs(num);
  const sign = num < 0 ? '-' : '';

  if (abs >= 10000000) { // 1 Crore
    const cr = abs / 10000000;
    return `${sign}Rs. ${cr.toFixed(2)} Cr`;
  } else if (abs >= 100000) { // 1 Lakh
    const lk = abs / 100000;
    return `${sign}Rs. ${lk.toFixed(2)} Lkh`;
  } else if (abs >= 1000) { // 1 Thousand
    const th = abs / 1000;
    return `${sign}Rs. ${th.toFixed(2)} Th`;
  } else {
    return `${sign}Rs. ${formatIndianNumber(abs, 2)}`;
  }
}

function formatChartAxisTick(v) {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 10000000) return `${sign}Rs. ${(abs / 10000000).toFixed(1)} Cr`;
  if (abs >= 100000) return `${sign}Rs. ${(abs / 100000).toFixed(1)} Lakh`;
  if (abs >= 1000) return `${sign}Rs. ${(abs / 1000).toFixed(0)} k`;
  return `${sign}Rs. ${abs}`;
}

// DOM References
const elements = {
  viewAuth: document.getElementById('viewAuth'),
  viewChat: document.getElementById('viewChat'),
  viewReports: document.getElementById('viewReports'),
  navTabs: document.getElementById('navTabs'),
  navUserControls: document.getElementById('navUserControls'),
  userClientName: document.getElementById('userClientName'),
  btnLogout: document.getElementById('btnLogout'),
  tabChatBtn: document.getElementById('tabChatBtn'),
  tabReportsBtn: document.getElementById('tabReportsBtn'),

  // Auth
  usernameInput: document.getElementById('usernameInput'),
  passwordInput: document.getElementById('passwordInput'),
  btnLoginSubmit: document.getElementById('btnLoginSubmit'),
  loginError: document.getElementById('loginError'),
  demoAlphaBtn: document.getElementById('demoAlphaBtn'),
  demoBetaBtn: document.getElementById('demoBetaBtn'),

  // Chat
  chatStream: document.getElementById('chatStream'),
  chatInputField: document.getElementById('chatInputField'),
  btnSendChat: document.getElementById('btnSendChat'),
  suggestedChipsContainer: document.getElementById('suggestedChipsContainer'),
  chatClientSubtitle: document.getElementById('chatClientSubtitle'),

  // Reports & Slicers
  slicersDynamicContainer: document.getElementById('slicersDynamicContainer'),
  filteredCountText: document.getElementById('filteredCountText'),
  btnResetSlicers: document.getElementById('btnResetSlicers'),
  btnExportFilteredCsv: document.getElementById('btnExportFilteredCsv'),
  btnExportLedgerCsv: document.getElementById('btnExportLedgerCsv'),
  btnExportMatrixCsv: document.getElementById('btnExportMatrixCsv'),
  btnOpenExecutiveBriefing: document.getElementById('btnOpenExecutiveBriefing'),
  btnOpenCustomDossier: document.getElementById('btnOpenCustomDossier'),

  // KPIs
  kpiLabelRevenue: document.getElementById('kpiLabelRevenue'),
  kpiValRevenue: document.getElementById('kpiValRevenue'),
  kpiSubRevenue: document.getElementById('kpiSubRevenue'),
  kpiLabelVolume: document.getElementById('kpiLabelVolume'),
  kpiValVolume: document.getElementById('kpiValVolume'),
  kpiSubVolume: document.getElementById('kpiSubVolume'),
  kpiLabelRealization: document.getElementById('kpiLabelRealization'),
  kpiValRealization: document.getElementById('kpiValRealization'),
  kpiSubRealization: document.getElementById('kpiSubRealization'),
  kpiLabelQuality: document.getElementById('kpiLabelQuality'),
  kpiValQuality: document.getElementById('kpiValQuality'),
  kpiSubQuality: document.getElementById('kpiSubQuality'),
  kpiLabelCustom: document.getElementById('kpiLabelCustom'),
  kpiValCustom: document.getElementById('kpiValCustom'),
  kpiSubCustom: document.getElementById('kpiSubCustom'),

  // Chart Canvases
  trendChartCanvas: document.getElementById('trendChartCanvas'),
  donutChartCanvas: document.getElementById('donutChartCanvas'),
  rankingChartCanvas: document.getElementById('rankingChartCanvas'),
  channelChartCanvas: document.getElementById('channelChartCanvas'),

  // Matrix Table
  matrixDataTable: document.getElementById('matrixDataTable'),
  matrixTableBody: document.getElementById('matrixTableBody'),
  matrixTableTitle: document.getElementById('matrixTableTitle'),

  // Records Table
  rawTableHead: document.getElementById('rawTableHead'),
  rawTableBody: document.getElementById('rawTableBody'),
  recordSearchInput: document.getElementById('recordSearchInput'),

  // Modals
  briefingModal: document.getElementById('briefingModal'),
  btnCloseBriefing: document.getElementById('btnCloseBriefing'),
  briefingContentPlaceholder: document.getElementById('briefingContentPlaceholder'),

  customDossierModal: document.getElementById('customDossierModal'),
  btnCloseCustomDossier: document.getElementById('btnCloseCustomDossier'),
  btnPrintDossier: document.getElementById('btnPrintDossier'),
  btnDownloadHtmlDossier: document.getElementById('btnDownloadHtmlDossier'),
  dossierModalBody: document.getElementById('dossierModalBody'),
  dossierSubtitle: document.getElementById('dossierSubtitle'),

  // ERP Health Telemetry Pill
  erpHealthPill: document.getElementById('erpHealthPill'),
  erpHealthDot: document.getElementById('erpHealthDot'),
  erpHealthText: document.getElementById('erpHealthText')
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  if (state.token) {
    await verifySession();
  } else {
    showView('auth');
  }
});

function setupEventListeners() {
  // Navigation Tabs
  elements.tabChatBtn.addEventListener('click', () => switchTab('chat'));
  elements.tabReportsBtn.addEventListener('click', () => switchTab('reports'));
  elements.btnLogout.addEventListener('click', handleLogout);

  // Auth
  elements.btnLoginSubmit.addEventListener('click', handleLogin);
  elements.usernameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleLogin(); });
  elements.passwordInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleLogin(); });

  elements.demoAlphaBtn.addEventListener('click', () => {
    elements.usernameInput.value = 'client_alpha';
    elements.passwordInput.value = 'himalayan_secret';
    handleLogin();
  });

  elements.demoBetaBtn.addEventListener('click', () => {
    elements.usernameInput.value = 'client_beta';
    elements.passwordInput.value = 'zenith_secret';
    handleLogin();
  });

  // Chat
  elements.btnSendChat.addEventListener('click', submitChatMessage);
  elements.chatInputField.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitChatMessage();
  });

  // Slicers & Reports
  elements.btnResetSlicers.addEventListener('click', resetSlicers);
  elements.btnExportFilteredCsv.addEventListener('click', exportFilteredData);
  if (elements.btnExportLedgerCsv) {
    elements.btnExportLedgerCsv.addEventListener('click', exportFilteredData);
  }
  if (elements.btnExportMatrixCsv) {
    elements.btnExportMatrixCsv.addEventListener('click', exportMatrixData);
  }
  elements.btnOpenExecutiveBriefing.addEventListener('click', openExecutiveBriefing);
  elements.btnCloseBriefing.addEventListener('click', () => {
    elements.briefingModal.classList.remove('active');
  });

  // Dossier Modal
  if (elements.btnOpenCustomDossier) {
    elements.btnOpenCustomDossier.addEventListener('click', openCustomDossier);
  }
  if (elements.btnCloseCustomDossier) {
    elements.btnCloseCustomDossier.addEventListener('click', () => {
      elements.customDossierModal.classList.remove('active');
    });
  }
  if (elements.btnPrintDossier) {
    elements.btnPrintDossier.addEventListener('click', printCustomDossier);
  }
  if (elements.btnDownloadHtmlDossier) {
    elements.btnDownloadHtmlDossier.addEventListener('click', downloadHtmlDossier);
  }

  // Records Search
  elements.recordSearchInput.addEventListener('input', filterRawRecordsTable);

  // Oracle Live ERP Sync
  if (elements.btnSyncOracle) {
    elements.btnSyncOracle.addEventListener('click', handleSyncOracle);
  }
}

// ==============================================================================
// AUTHENTICATION & SESSION MANAGEMENT
// ==============================================================================
async function handleLogin() {
  const username = elements.usernameInput.value.trim();
  const password = elements.passwordInput.value.trim();

  elements.loginError.style.display = 'none';
  if (!username || !password) {
    showLoginError('Please provide both username and password.');
    return;
  }

  elements.btnLoginSubmit.disabled = true;
  elements.btnLoginSubmit.textContent = 'Authenticating...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      showLoginError(data.detail || 'Authentication failed.');
      return;
    }

    state.token = data.token;
    localStorage.setItem('camellia_token', data.token);
    state.client = {
      client_id: data.client_id,
      client_name: data.client_name,
      description: data.description,
      industry_focus: data.industry_focus,
      suggested_questions: data.suggested_questions
    };

    onLoginSuccess();
  } catch (err) {
    showLoginError('Network or server connection error. Ensure FastAPI server is running.');
  } finally {
    elements.btnLoginSubmit.disabled = false;
    elements.btnLoginSubmit.textContent = 'Access Tea Ledger';
  }
}

async function verifySession() {
  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (!res.ok) {
      handleLogout();
      return;
    }
    const data = await res.json();
    state.client = {
      client_id: data.client_id,
      client_name: data.client_name,
      description: data.description,
      industry_focus: data.industry_focus,
      suggested_questions: data.suggested_questions
    };
    onLoginSuccess();
  } catch (e) {
    handleLogout();
  }
}

function onLoginSuccess() {
  elements.userClientName.textContent = state.client.client_name;
  elements.chatClientSubtitle.textContent = `${state.client.client_name} • Executive Intelligence`;

  elements.navTabs.style.display = 'flex';
  elements.navUserControls.style.display = 'flex';

  updateErpHealthPill();
  renderSuggestedChips();
  initWelcomeChat();
  switchTab('chat');
}

function handleLogout() {
  state.token = null;
  state.client = null;
  localStorage.removeItem('camellia_token');
  elements.navTabs.style.display = 'none';
  elements.navUserControls.style.display = 'none';
  elements.usernameInput.value = '';
  elements.passwordInput.value = '';
  showView('auth');
}

function showLoginError(msg) {
  elements.loginError.textContent = msg;
  elements.loginError.style.display = 'block';
}

function showView(view) {
  elements.viewAuth.style.display = view === 'auth' ? 'grid' : 'none';
  elements.viewChat.style.display = view === 'chat' ? 'flex' : 'none';
  elements.viewReports.style.display = view === 'reports' ? 'flex' : 'none';
}

function switchTab(tab) {
  state.activeTab = tab;
  if (tab === 'chat') {
    elements.tabChatBtn.classList.add('active');
    elements.tabReportsBtn.classList.remove('active');
    showView('chat');
  } else if (tab === 'reports') {
    elements.tabReportsBtn.classList.add('active');
    elements.tabChatBtn.classList.remove('active');
    showView('reports');
    loadReportsDashboard();
    // Force Chart.js instances to dynamically snap to visible container width
    setTimeout(() => {
      if (state.charts) {
        Object.values(state.charts).forEach(chart => {
          if (chart && typeof chart.resize === 'function') {
            chart.resize();
          }
        });
      }
    }, 60);
  }
}

async function handleSyncOracle() {
  // Oracle sync removed
}

// ==============================================================================
// CHATBOT CONTROLLER (Executive Lead Answer & Insights)
// ==============================================================================
function renderSuggestedChips() {
  elements.suggestedChipsContainer.innerHTML = '';
  const questions = state.client.suggested_questions || [
    'What is total revenue and volume?',
    'Which product/grade leads performance?',
    'Analyze distribution channels and margins'
  ];

  questions.forEach(q => {
    const chip = document.createElement('button');
    chip.className = 'question-chip';
    chip.innerHTML = `<span>🍵</span><span>${escapeHtml(q)}</span>`;
    chip.addEventListener('click', () => {
      elements.chatInputField.value = q;
      submitChatMessage();
    });
    elements.suggestedChipsContainer.appendChild(chip);
  });
}

function initWelcomeChat() {
  elements.chatStream.innerHTML = '';
  if (!state.client) return;

  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';

  const clientName = escapeHtml(state.client.client_name || 'Enterprise Tea Intelligence');
  const role = escapeHtml(state.client.role || 'Executive Business Analyst');
  const industry = escapeHtml(state.client.industry_focus || state.client.industry || 'Tea Operations & Commerce');
  const desc = escapeHtml(state.client.description || 'Verified enterprise operational records.');

  const welcomeHtml = `
    <div class="chat-avatar">🍵</div>
    <div class="chat-bubble welcome-bubble">
      <h3 class="welcome-heading">Welcome to ${clientName}</h3>
      <p class="welcome-paragraph">
        I am your <strong>${role}</strong> specializing in <strong>${industry}</strong>.
      </p>
      <p class="welcome-paragraph">
        ${desc}
      </p>
      <p class="welcome-paragraph welcome-hint">
        Select one of the suggested prompts below or type any question into the chat bar to begin.
      </p>
    </div>
  `;

  msg.innerHTML = welcomeHtml;
  elements.chatStream.appendChild(msg);
}

async function submitChatMessage() {
  const query = elements.chatInputField.value.trim();
  if (!query) return;

  // Render user question
  renderUserMessage(query);
  elements.chatInputField.value = '';
  elements.btnSendChat.disabled = true;

  // Render loading placeholder
  const loadingBubble = renderLoadingBubble();

  try {
    const res = await fetch('/api/chat/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.token}`
      },
      body: JSON.stringify({
        question: query,
        conversation_context: state.conversationContext || {}
      })
    });

    const data = await res.json();
    loadingBubble.remove();

    if (!res.ok) {
      renderAssistantError(data.detail || 'Error processing request.');
      return;
    }

    if (data.conversation_context) {
      state.conversationContext = data.conversation_context;
    }

    renderAssistantMessage(data);
  } catch (err) {
    loadingBubble.remove();
    renderAssistantError('Server connectivity lost. Please verify backend status.');
  } finally {
    elements.btnSendChat.disabled = false;
  }
}

function renderUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'chat-message user';
  msg.innerHTML = `
    <div class="chat-avatar">👤</div>
    <div class="chat-bubble">
      <div>${escapeHtml(text)}</div>
    </div>
  `;
  elements.chatStream.appendChild(msg);
  elements.chatStream.scrollTop = elements.chatStream.scrollHeight;
}

function renderLoadingBubble() {
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';
  msg.innerHTML = `
    <div class="chat-avatar">🍵</div>
    <div class="chat-bubble" style="color: var(--text-muted); font-style: italic; display: flex; align-items: center; gap: 8px;">
      <span class="client-chip-dot"></span> Auditing ledger records and computing evidence...
    </div>
  `;
  elements.chatStream.appendChild(msg);
  elements.chatStream.scrollTop = elements.chatStream.scrollHeight;
  return msg;
}

function renderAssistantError(errorMsg) {
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';
  msg.innerHTML = `
    <div class="chat-avatar" style="background: var(--tea-terracotta);">⚠️</div>
    <div class="chat-bubble" style="border-left: 3px solid var(--tea-terracotta);">
      <strong style="color: var(--tea-terracotta);">Notice:</strong> ${escapeHtml(errorMsg)}
    </div>
  `;
  elements.chatStream.appendChild(msg);
  elements.chatStream.scrollTop = elements.chatStream.scrollHeight;
}

function renderAssistantMessage(data) {
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';

  // Format Evidence List (compact, max 2 items)
  let evidenceHtml = '';
  if (data.evidence && data.evidence.length > 0) {
    const listItems = data.evidence.slice(0, 2).map(item => `<li>${formatRichText(item)}</li>`).join('');
    evidenceHtml = `
      <div class="narrative-section">
        <div class="narrative-subtitle">Key Highlights</div>
        <ul class="narrative-evidence-list">${listItems}</ul>
      </div>
    `;
  }

  // Format Key Insights & Recommendations side-by-side in a compact briefing grid
  let briefingGridHtml = '';
  const insightsText = data.key_insights || data.why_root_cause;
  const recommendationsText = data.recommendations || data.action;

  if (insightsText || recommendationsText) {
    const whyBlock = insightsText ? `
      <div class="narrative-briefing-col">
        <div class="narrative-subtitle">Key Insight</div>
        <div class="narrative-why">${formatRichText(insightsText)}</div>
      </div>
    ` : '';
    const actionBlock = recommendationsText ? `
      <div class="narrative-briefing-col">
        <div class="narrative-subtitle">Recommendation</div>
        <div class="narrative-action">${formatRichText(recommendationsText)}</div>
      </div>
    ` : '';

    briefingGridHtml = `
      <div class="narrative-section">
        <div class="narrative-briefing-grid">
          ${whyBlock}
          ${actionBlock}
        </div>
      </div>
    `;
  }

  // Format Mini Chart (only when multi-item ranking chart is provided)
  let chartHtml = '';
  const chartCanvasId = 'chart_' + Math.random().toString(36).substring(2, 9);
  if (data.chart_data && data.chart_data.labels && data.chart_data.labels.length >= 2) {
    chartHtml = `
      <div class="narrative-chart-wrapper" style="margin: 8px 0; background: #fbfaf7; border-radius: 6px; padding: 10px 12px; border: 1px solid var(--border-light);">
        <div style="font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--tea-leaf); margin-bottom: 6px;">
          📊 ${escapeHtml(data.chart_data.title || 'Visual Distribution')}
        </div>
        <div style="height: 150px; position: relative;">
          <canvas id="${chartCanvasId}"></canvas>
        </div>
      </div>
    `;
  }

  // Format Follow-up Chips
  let followupsHtml = '';
  if (data.followup_questions && data.followup_questions.length > 0) {
    const chips = data.followup_questions.slice(0, 3).map(q =>
      `<button class="chat-followup-pill" data-query="${escapeHtml(q)}">${escapeHtml(q)}</button>`
    ).join('');
    followupsHtml = `
      <div class="chat-followups">
        ${chips}
      </div>
    `;
  }

  // AI Provenance Badge
  let badgeHtml = '';
  if (data.is_ai_generated) {
    badgeHtml = `<div class="ai-provenance-badge ai-badge-live" title="Generated in real-time by ${escapeHtml(data.ai_engine || 'Google Gemini')}">✨ Live AI Synthesized (${escapeHtml(data.ai_engine || 'Google Gemini')})</div>`;
  } else {
    badgeHtml = `<div class="ai-provenance-badge ai-badge-fallback" title="Calculated with 100% deterministic mathematical precision by DuckDB/Pandas. (Gemini API was unavailable or reached quota limit)">📐 Grounded Math Engine (Deterministic Fallback)</div>`;
  }

  msg.innerHTML = `
    <div class="chat-avatar">🍵</div>
    <div class="chat-bubble" style="width: 100%;">
      ${badgeHtml}
      <div class="narrative-card">
        <div class="narrative-lead">${formatRichText(data.answer || '')}</div>
        ${chartHtml}
        ${evidenceHtml}
        ${briefingGridHtml}
      </div>
      ${followupsHtml}
    </div>
  `;

  // Attach click events to follow-up pills
  const pillButtons = msg.querySelectorAll('.chat-followup-pill');
  pillButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-query');
      elements.chatInputField.value = q;
      submitChatMessage();
    });
  });

  // Track in chat history for customized report export
  state.chatHistory.push({
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    question: data.question || 'Analytical Inquiry',
    answer: data.answer || '',
    evidence: data.evidence || [],
    key_insights: data.key_insights || data.why_root_cause || '',
    recommendations: data.recommendations || data.action || '',
    chart_data: data.chart_data || null
  });

  elements.chatStream.appendChild(msg);

  // Render Chart if Canvas exists
  if (data.chart_data && data.chart_data.labels && data.chart_data.labels.length >= 2) {
    const canvas = document.getElementById(chartCanvasId);
    if (canvas && window.Chart) {
      const isDonut = data.chart_data.type === 'donut';
      const isLine = data.chart_data.type === 'line';
      const chartType = isDonut ? 'doughnut' : (isLine ? 'line' : 'bar');
      try {
        new Chart(canvas, {
          type: chartType,
          data: {
            labels: data.chart_data.labels,
            datasets: (data.chart_data.datasets && data.chart_data.datasets.length > 0) ? data.chart_data.datasets : [{
              data: data.chart_data.values,
              backgroundColor: isDonut ? TEA_PALETTE.colors : (isLine ? 'rgba(45, 106, 79, 0.15)' : '#2d6a4f'),
              borderColor: isLine ? '#2d6a4f' : undefined,
              borderWidth: isLine ? 2 : undefined,
              fill: isLine,
              tension: isLine ? 0.35 : undefined,
              pointRadius: isLine ? 3 : undefined,
              pointBackgroundColor: isLine ? '#1b4332' : undefined,
              borderRadius: isDonut || isLine ? 0 : 4,
              barThickness: isLine ? undefined : 18,
              maxBarThickness: isLine ? undefined : 24,
              barPercentage: isLine ? undefined : 0.75
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: isDonut || !!(data.chart_data && data.chart_data.datasets && data.chart_data.datasets.length > 0),
                position: isDonut ? 'right' : 'top',
                labels: { boxWidth: 12, font: { size: 11, weight: '500' } }
              },
              tooltip: {
                callbacks: {
                  label: function (ctx) {
                    const val = ctx.raw;
                    const isKg = data.chart_data && data.chart_data.metric === 'kg';
                    const isPct = data.chart_data && data.chart_data.metric === 'percent';
                    let formatted = '';
                    if (isKg) {
                      formatted = formatIndianNumber(val, 3) + ' kgs';
                    } else if (isPct) {
                      formatted = Number(val).toFixed(1) + '%';
                    } else {
                      formatted = formatIndianCurrency(val);
                    }
                    const code = (data.chart_data && data.chart_data.codes && data.chart_data.codes[ctx.dataIndex]) ? ` [Code: ${data.chart_data.codes[ctx.dataIndex]}]` : '';
                    return ' ' + formatted + code;
                  }
                }
              }
            },
            scales: isDonut ? {} : {
              x: { ticks: { font: { size: 9 }, maxRotation: 25 } },
              y: {
                ticks: {
                  font: { size: 9 },
                  callback: function (v) {
                    if (data.chart_data && data.chart_data.metric === 'kg') {
                      const abs = Math.abs(v);
                      const sign = v < 0 ? '-' : '';
                      if (abs >= 100000) return `${sign}${(abs / 100000).toFixed(1)} L kgs`;
                      if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)}k kgs`;
                      return `${sign}${abs} kgs`;
                    }
                    return formatChartAxisTick(v);
                  }
                }
              }
            }
          }
        });
      } catch (e) {
        console.warn('Mini chart render note:', e);
      }
    }
  }

  elements.chatStream.scrollTop = elements.chatStream.scrollHeight;
}

// ==============================================================================
// POWER BI REPORTS & SLICER DASHBOARD
// ==============================================================================
let reportsInitialized = false;
let currentClientSlicers = null;

async function loadReportsDashboard() {
  const activeCid = state.client ? state.client.client_id : '';
  if (!reportsInitialized || currentClientSlicers !== activeCid) {
    await initSlicers();
    reportsInitialized = true;
    currentClientSlicers = activeCid;
  }
  await refreshDashboardData();
}

function renderDateRangeSlicer(container, data) {
  if (!data.date_min || !data.date_max) return;

  const minDateStr = data.date_min;
  const maxDateStr = data.date_max;
  const minTime = new Date(minDateStr + 'T00:00:00').getTime();
  const maxTime = new Date(maxDateStr + 'T00:00:00').getTime();
  const totalSpan = maxTime - minTime || 1;

  const dropdown = document.createElement('div');
  dropdown.className = 'ms-slicer-dropdown ms-date-range-dropdown';
  dropdown.id = 'dropdown_date_range';

  // Build FY options for quick buttons
  const fyList = data.financial_years || [];
  const fyButtons = fyList.slice(0, 3).map(fy => `
    <button type="button" class="ms-date-pill" data-preset="fy" data-val="${escapeHtml(fy)}">${escapeHtml(fy)}</button>
  `).join('');

  dropdown.innerHTML = `
    <button type="button" class="ms-slicer-btn ms-date-pin-btn" id="slicerBtn_date_range">
      <span class="ms-slicer-label">📅 Timeline:</span>
      <span class="ms-slicer-summary" id="slicerSummary_date_range">All Time</span>
      <span class="ms-slicer-chevron">▾</span>
    </button>
    <div class="ms-slicer-menu ms-date-slicer-menu ms-pinterest-card" id="slicerMenu_date_range">
      <div class="ms-date-pin-header">
        <div class="ms-date-pin-title">
          <span class="ms-pin-sparkle">✦</span>
          <span>Date Scope</span>
        </div>
        <span id="dateRangeDurationBadge" class="ms-date-pin-badge">All Dates</span>
      </div>

      <div class="ms-date-body">
        <div class="ms-date-presets-row" id="datePresetPills">
          <button type="button" class="ms-date-pill active" data-preset="all">All Time</button>
          ${fyButtons}
          ${(data.years || []).slice(-2).reverse().map(y => `
            <button type="button" class="ms-date-pill" data-preset="year" data-val="${escapeHtml(y)}">${escapeHtml(y)}</button>
          `).join('')}
        </div>

        <div class="ms-date-scrubber-card">
          <div class="ms-date-drag-track" id="dualSliderTrack">
            <div id="sliderFillHighlight" class="ms-date-drag-fill" style="left: 0%; right: 0%;"></div>
            <input type="range" id="sliderThumbStart" min="0" max="1000" value="0" class="ms-date-thumb" aria-label="Start date slider">
            <input type="range" id="sliderThumbEnd" min="0" max="1000" value="1000" class="ms-date-thumb" aria-label="End date slider">
          </div>
          <div class="ms-date-drag-legend">
            <span class="ms-date-edge-label">${minDateStr}</span>
            <span id="sliderRangeSpanText" class="ms-date-drag-span">Full Range</span>
            <span class="ms-date-edge-label">${maxDateStr}</span>
          </div>
        </div>

        <div class="ms-date-pickers-row">
          <div class="ms-date-field-col">
            <label class="ms-date-field-label" for="datePickerStart">From</label>
            <input type="date" id="datePickerStart" class="ms-date-pin-input" value="${minDateStr}" min="${minDateStr}" max="${maxDateStr}">
          </div>
          <div class="ms-date-field-sep">→</div>
          <div class="ms-date-field-col">
            <label class="ms-date-field-label" for="datePickerEnd">To</label>
            <input type="date" id="datePickerEnd" class="ms-date-pin-input" value="${maxDateStr}" min="${minDateStr}" max="${maxDateStr}">
          </div>
        </div>

        <div class="ms-date-actions-row">
          <button type="button" id="btnDateClear" class="ms-date-btn-secondary">Reset</button>
          <button type="button" id="btnDateApply" class="ms-date-btn-primary">Apply ✓</button>
        </div>
      </div>
    </div>
  `;

  container.appendChild(dropdown);

  const btn = dropdown.querySelector('#slicerBtn_date_range');
  const menu = dropdown.querySelector('#slicerMenu_date_range');
  const summary = dropdown.querySelector('#slicerSummary_date_range');
  const inputStart = dropdown.querySelector('#datePickerStart');
  const inputEnd = dropdown.querySelector('#datePickerEnd');
  const thumbStart = dropdown.querySelector('#sliderThumbStart');
  const thumbEnd = dropdown.querySelector('#sliderThumbEnd');
  const fillHighlight = dropdown.querySelector('#sliderFillHighlight');
  const spanText = dropdown.querySelector('#sliderRangeSpanText');
  const presetPills = dropdown.querySelectorAll('.ms-date-pill');
  const btnClear = dropdown.querySelector('#btnDateClear');
  const btnApply = dropdown.querySelector('#btnDateApply');

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const wasOpen = dropdown.classList.contains('open');
    document.querySelectorAll('.ms-slicer-dropdown.open').forEach(d => d.classList.remove('open'));
    if (!wasOpen) dropdown.classList.add('open');
  });

  menu.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  function updateTrackVisuals() {
    let sVal = parseInt(thumbStart.value, 10);
    let eVal = parseInt(thumbEnd.value, 10);
    if (sVal > eVal) {
      thumbStart.value = eVal;
      sVal = eVal;
    }
    const leftPct = (sVal / 1000) * 100;
    const rightPct = 100 - (eVal / 1000) * 100;
    fillHighlight.style.left = `${leftPct}%`;
    fillHighlight.style.right = `${rightPct}%`;
  }

  const durationBadge = dropdown.querySelector('#dateRangeDurationBadge');

  function updateDurationBadge() {
    if (!durationBadge) return;
    const s = new Date((inputStart.value || minDateStr) + 'T00:00:00');
    const e = new Date((inputEnd.value || maxDateStr) + 'T00:00:00');
    const diffDays = Math.max(1, Math.round((e - s) / (1000 * 60 * 60 * 24)));
    if (inputStart.value <= minDateStr && inputEnd.value >= maxDateStr) {
      durationBadge.textContent = 'Full Scope';
    } else {
      durationBadge.textContent = `${diffDays} Days`;
    }
  }

  function syncInputsFromSliders() {
    updateTrackVisuals();
    const sVal = parseInt(thumbStart.value, 10);
    const eVal = parseInt(thumbEnd.value, 10);
    const sTime = minTime + (sVal / 1000) * totalSpan;
    const eTime = minTime + (eVal / 1000) * totalSpan;
    inputStart.value = new Date(sTime).toISOString().slice(0, 10);
    inputEnd.value = new Date(eTime).toISOString().slice(0, 10);
    spanText.textContent = `${inputStart.value} to ${inputEnd.value}`;
    updateDurationBadge();
  }

  function syncSlidersFromInputs() {
    const sTime = new Date((inputStart.value || minDateStr) + 'T00:00:00').getTime();
    const eTime = new Date((inputEnd.value || maxDateStr) + 'T00:00:00').getTime();
    const sRatio = Math.max(0, Math.min(1000, Math.round(((sTime - minTime) / totalSpan) * 1000)));
    const eRatio = Math.max(0, Math.min(1000, Math.round(((eTime - minTime) / totalSpan) * 1000)));
    thumbStart.value = sRatio;
    thumbEnd.value = eRatio;
    updateTrackVisuals();
    spanText.textContent = `${inputStart.value} to ${inputEnd.value}`;
    updateDurationBadge();
  }

  thumbStart.addEventListener('input', () => {
    presetPills.forEach(p => p.classList.remove('active'));
    syncInputsFromSliders();
  });

  thumbEnd.addEventListener('input', () => {
    presetPills.forEach(p => p.classList.remove('active'));
    syncInputsFromSliders();
  });

  inputStart.addEventListener('change', () => {
    presetPills.forEach(p => p.classList.remove('active'));
    syncSlidersFromInputs();
  });

  inputEnd.addEventListener('change', () => {
    presetPills.forEach(p => p.classList.remove('active'));
    syncSlidersFromInputs();
  });

  function applyDateRange(labelOverride) {
    const sVal = inputStart.value;
    const eVal = inputEnd.value;
    const isFull = (sVal <= minDateStr && eVal >= maxDateStr);

    if (isFull && !labelOverride) {
      delete state.filters.date_start;
      delete state.filters.date_end;
      summary.textContent = 'All';
    } else {
      state.filters.date_start = sVal;
      state.filters.date_end = eVal;
      if (labelOverride) {
        summary.textContent = labelOverride;
      } else {
        summary.textContent = `${sVal.slice(2)} → ${eVal.slice(2)}`;
      }
    }
    dropdown.classList.remove('open');
    refreshDashboardData();
  }

  btnApply.addEventListener('click', () => {
    applyDateRange();
  });

  btnClear.addEventListener('click', () => {
    inputStart.value = minDateStr;
    inputEnd.value = maxDateStr;
    syncSlidersFromInputs();
    spanText.textContent = 'All Dates';
    presetPills.forEach(p => p.classList.remove('active'));
    const allPill = dropdown.querySelector('.ms-date-pill[data-preset="all"]');
    if (allPill) allPill.classList.add('active');
    delete state.filters.date_start;
    delete state.filters.date_end;
    summary.textContent = 'All';
    dropdown.classList.remove('open');
    refreshDashboardData();
  });

  presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      presetPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const pType = pill.getAttribute('data-preset');
      const pVal = pill.getAttribute('data-val');

      if (pType === 'all') {
        inputStart.value = minDateStr;
        inputEnd.value = maxDateStr;
        syncSlidersFromInputs();
        applyDateRange('All');
      } else if (pType === 'fy') {
        const m = pVal.match(/20\d\d/);
        if (m) {
          const startYr = parseInt(m[0], 10);
          inputStart.value = `${startYr}-04-01`;
          inputEnd.value = `${startYr + 1}-03-31`;
          syncSlidersFromInputs();
          applyDateRange(pVal);
        }
      } else if (pType === 'year') {
        inputStart.value = `${pVal}-01-01`;
        inputEnd.value = `${pVal}-12-31`;
        syncSlidersFromInputs();
        applyDateRange(pVal);
      }
    });
  });
}

async function initSlicers() {
  const container = elements.slicersDynamicContainer;
  if (!container) return;

  try {
    const res = await fetch('/api/reports/filters', {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    const slicers = data.slicers || [];

    state.slicersConfig = slicers;
    container.innerHTML = '';
    state.filters = {};

    // Inline Date Range Slicer (calendar + dual scrubber + FY presets)
    renderDateRangeSlicer(container, data);

    slicers.forEach(slicer => {
      state.filters[slicer.key] = ['All'];

      const dropdown = document.createElement('div');
      dropdown.className = 'ms-slicer-dropdown';
      dropdown.id = `dropdown_${slicer.key}`;
      dropdown.dataset.slicer = slicer.key;

      const optsCount = (slicer.options || []).length;
      const hasSearch = optsCount > 6;

      dropdown.innerHTML = `
        <button type="button" class="ms-slicer-btn" id="slicerBtn_${slicer.key}">
          <span class="ms-slicer-label">${escapeHtml(slicer.label)}:</span>
          <span class="ms-slicer-summary" id="slicerSummary_${slicer.key}">All</span>
          <span class="ms-slicer-chevron">▾</span>
        </button>
        <div class="ms-slicer-menu" id="slicerMenu_${slicer.key}">
          <div class="ms-slicer-header">
            <label class="ms-slicer-item ms-select-all">
              <input type="checkbox" id="chkAll_${slicer.key}" value="All" checked>
              <span>(Select All)</span>
            </label>
          </div>
          ${hasSearch ? `
            <div class="ms-slicer-search">
              <input type="text" placeholder="Search ${escapeHtml(slicer.label)}..." class="ms-search-input" id="search_${slicer.key}">
            </div>
          ` : ''}
          <div class="ms-slicer-divider"></div>
          <div class="ms-slicer-options" id="slicerOpts_${slicer.key}">
            ${(slicer.options || []).map(opt => `
              <label class="ms-slicer-item" data-val="${escapeHtml(String(opt).toLowerCase())}">
                <input type="checkbox" value="${escapeHtml(String(opt))}" checked>
                <span>${escapeHtml(String(opt))}</span>
              </label>
            `).join('')}
          </div>
        </div>
      `;

      container.appendChild(dropdown);

      // Event listeners for this slicer
      const btn = dropdown.querySelector(`#slicerBtn_${slicer.key}`);
      const menu = dropdown.querySelector(`#slicerMenu_${slicer.key}`);
      const chkAll = dropdown.querySelector(`#chkAll_${slicer.key}`);
      const summary = dropdown.querySelector(`#slicerSummary_${slicer.key}`);
      const optsContainer = dropdown.querySelector(`#slicerOpts_${slicer.key}`);
      const searchInput = dropdown.querySelector(`#search_${slicer.key}`);

      // Toggle dropdown open/close
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasOpen = dropdown.classList.contains('open');
        document.querySelectorAll('.ms-slicer-dropdown.open').forEach(d => d.classList.remove('open'));
        if (!wasOpen) dropdown.classList.add('open');
      });

      menu.addEventListener('click', (e) => {
        e.stopPropagation();
      });

      // Search input filter
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          const q = e.target.value.toLowerCase().trim();
          const items = optsContainer.querySelectorAll('.ms-slicer-item');
          items.forEach(it => {
            const v = it.getAttribute('data-val') || '';
            it.style.display = v.includes(q) ? 'flex' : 'none';
          });
        });
      }

      // Select All toggle
      chkAll.addEventListener('change', () => {
        const isChecked = chkAll.checked;
        const itemBoxes = Array.from(optsContainer.querySelectorAll('input[type="checkbox"]'));
        itemBoxes.forEach(cb => { cb.checked = isChecked; });

        if (isChecked) {
          state.filters[slicer.key] = ['All'];
          summary.textContent = 'All';
        } else {
          state.filters[slicer.key] = [];
          summary.textContent = 'None';
        }
        refreshDashboardData();
      });

      // Individual options toggle
      optsContainer.addEventListener('change', (e) => {
        if (!e.target || e.target.type !== 'checkbox') return;
        const allBoxes = Array.from(optsContainer.querySelectorAll('input[type="checkbox"]'));
        const checkedBoxes = allBoxes.filter(cb => cb.checked);
        const checkedVals = checkedBoxes.map(cb => cb.value);

        if (checkedBoxes.length === allBoxes.length) {
          chkAll.checked = true;
          state.filters[slicer.key] = ['All'];
          summary.textContent = 'All';
        } else if (checkedBoxes.length === 0) {
          chkAll.checked = false;
          state.filters[slicer.key] = [];
          summary.textContent = 'None';
        } else {
          chkAll.checked = false;
          state.filters[slicer.key] = checkedVals;
          if (checkedVals.length === 1) {
            summary.textContent = checkedVals[0];
          } else if (checkedVals.length === 2) {
            summary.textContent = `${checkedVals[0].slice(0, 4)}, ${checkedVals[1].slice(0, 4)}`;
          } else {
            summary.textContent = `${checkedVals.length} sel`;
          }
        }
        refreshDashboardData();
      });
    });

  } catch (e) {
    console.error('Failed to initialize client slicers', e);
  }
}

// Global click to close open slicer dropdowns
document.addEventListener('click', (e) => {
  const openDropdowns = document.querySelectorAll('.ms-slicer-dropdown.open');
  openDropdowns.forEach(dd => {
    if (!dd.contains(e.target)) {
      dd.classList.remove('open');
    }
  });
});

function resetSlicers() {
  delete state.filters.date_start;
  delete state.filters.date_end;
  const dateSummary = document.getElementById('slicerSummary_date_range');
  if (dateSummary) dateSummary.textContent = 'All Dates';
  const allPill = document.querySelector('.ms-preset-pill[data-preset="all"]');
  if (allPill) {
    document.querySelectorAll('.ms-preset-pill').forEach(p => p.classList.remove('active'));
    allPill.classList.add('active');
  }

  if (!state.slicersConfig) return;
  state.slicersConfig.forEach(slicer => {
    state.filters[slicer.key] = ['All'];
    const summary = document.getElementById(`slicerSummary_${slicer.key}`);
    if (summary) summary.textContent = 'All';
    const chkAll = document.getElementById(`chkAll_${slicer.key}`);
    if (chkAll) chkAll.checked = true;
    const optsContainer = document.getElementById(`slicerOpts_${slicer.key}`);
    if (optsContainer) {
      optsContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => { cb.checked = true; });
    }
    const searchInput = document.getElementById(`search_${slicer.key}`);
    if (searchInput) {
      searchInput.value = '';
      if (optsContainer) {
        optsContainer.querySelectorAll('.ms-slicer-item').forEach(it => { it.style.display = 'flex'; });
      }
    }
  });
  refreshDashboardData();
}

function buildSlicerQuery() {
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(state.filters)) {
    if (!val) continue;
    if (Array.isArray(val)) {
      if (val.length > 0 && !val.includes('All')) {
        params.append(key, val.join(','));
      }
    } else if (typeof val === 'string' && val !== 'All' && val !== '') {
      params.append(key, val);
    }
  }
  return params.toString();
}

async function refreshDashboardData() {
  const query = buildSlicerQuery();
  const authHeader = { 'Authorization': `Bearer ${state.token}` };

  // Parallel fetch for KPIs, Charts, Matrix, Records
  try {
    const [kpiRes, chartRes, matrixRes, recordRes] = await Promise.all([
      fetch(`/api/reports/kpis?${query}`, { headers: authHeader }),
      fetch(`/api/reports/charts?${query}`, { headers: authHeader }),
      fetch(`/api/reports/matrix?${query}`, { headers: authHeader }),
      fetch(`/api/reports/records?${query}&limit=200`, { headers: authHeader })
    ]);

    if (kpiRes && kpiRes.ok) {
      try {
        const kpis = await kpiRes.json();
        renderKpis(kpis);
      } catch (err) { console.error('Error rendering KPIs', err); }
    }

    if (chartRes && chartRes.ok) {
      try {
        const charts = await chartRes.json();
        renderCharts(charts);
      } catch (err) { console.error('Error rendering charts', err); }
    }

    if (matrixRes && matrixRes.ok) {
      try {
        const matrix = await matrixRes.json();
        renderMatrix(matrix);
      } catch (err) { console.error('Error rendering matrix', err); }
    }

    if (recordRes && recordRes.ok) {
      try {
        const recs = await recordRes.json();
        state.rawRecords = recs.records || [];
        renderRawRecordsTable(recs.records || []);
      } catch (err) { console.error('Error rendering records table', err); }
    }
  } catch (e) {
    console.error('Error refreshing dashboard data', e);
  }
}

// ------------------------------------------------------------------------------
// KPI RENDERING
// ------------------------------------------------------------------------------
function renderKpis(data) {
  if (!data || !data.kpis) return;
  state.lastKpiData = data;

  const countEl = document.getElementById('filteredCountText');
  if (countEl) {
    countEl.textContent = `${Number(data.record_count || 0).toLocaleString()} records`;
  }

  const setCard = (prefix, kpiObj) => {
    if (!kpiObj) return;
    const lbl = document.getElementById(`kpiLabel${prefix}`);
    const val = document.getElementById(`kpiVal${prefix}`);
    const sub = document.getElementById(`kpiSub${prefix}`);
    if (lbl && kpiObj.label) lbl.textContent = kpiObj.label;
    if (val && kpiObj.value !== undefined) val.textContent = kpiObj.value;
    if (sub && kpiObj.sub) sub.textContent = kpiObj.sub;
  };

  setCard('Revenue', data.kpis.revenue);
  setCard('Volume', data.kpis.volume);
  setCard('Realization', data.kpis.realization);
  setCard('Quality', data.kpis.quality);
  setCard('Custom', data.kpis.custom);
}

// ------------------------------------------------------------------------------
// CHART.JS POWER BI RENDERING: SUBSTANTIAL & THICK BARS
// ------------------------------------------------------------------------------
function renderCharts(data) {
  if (data.monthly_trend && data.monthly_trend.title) {
    const el = document.getElementById('trendChartTitle');
    if (el) el.textContent = data.monthly_trend.title;
  }
  if (data.monthly_trend && data.monthly_trend.tag) {
    const el = document.getElementById('trendChartTag');
    if (el) el.textContent = data.monthly_trend.tag;
  }

  if (data.category_share && data.category_share.title) {
    const el = document.getElementById('donutChartTitle');
    if (el) el.textContent = data.category_share.title;
  }
  if (data.category_share && data.category_share.tag) {
    const el = document.getElementById('donutChartTag');
    if (el) el.textContent = data.category_share.tag;
  }

  if (data.ranking_leaders && data.ranking_leaders.title) {
    const el = document.getElementById('rankingChartTitle');
    if (el) el.textContent = data.ranking_leaders.title;
  }
  if (data.ranking_leaders && data.ranking_leaders.tag) {
    const el = document.getElementById('rankingChartTag');
    if (el) el.textContent = data.ranking_leaders.tag;
  }

  if (data.channel_distribution && data.channel_distribution.title) {
    const el = document.getElementById('channelChartTitle');
    if (el) el.textContent = data.channel_distribution.title;
  }
  if (data.channel_distribution && data.channel_distribution.tag) {
    const el = document.getElementById('channelChartTag');
    if (el) el.textContent = data.channel_distribution.tag;
  }

  renderTrendChart(data.monthly_trend);
  renderDonutChart(data.category_share);
  renderRankingChart(data.ranking_leaders);
  renderChannelChart(data.channel_distribution);
}

function renderTrendChart(trendData) {
  if (state.charts.trend) state.charts.trend.destroy();
  const ctx = elements.trendChartCanvas.getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, 'rgba(45, 106, 79, 0.32)');
  gradient.addColorStop(1, 'rgba(45, 106, 79, 0.00)');

  state.charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trendData.labels || [],
      datasets: [{
        label: 'Monthly Revenue (Rs.)',
        data: trendData.values || [],
        borderColor: TEA_PALETTE.leaf,
        borderWidth: 2.2,
        pointBackgroundColor: TEA_PALETTE.forest,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        pointRadius: 3,
        pointHoverRadius: 5.5,
        fill: true,
        backgroundColor: gradient,
        tension: 0.35
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1b4332',
          titleFont: { family: 'Plus Jakarta Sans', size: 10 },
          bodyFont: { family: 'Plus Jakarta Sans', size: 10 },
          callbacks: {
            label: (ctx) => ` Revenue: ${formatIndianCurrency(ctx.raw)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 9 },
            color: '#647a6b',
            autoSkip: true,
            maxTicksLimit: 10,
            maxRotation: 45,
            minRotation: 0
          }
        },
        y: {
          grid: { color: 'rgba(226, 232, 228, 0.5)' },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 9 },
            color: '#647a6b',
            callback: (v) => formatChartAxisTick(v)
          }
        }
      }
    }
  });
}

function renderDonutChart(shareData) {
  if (state.charts.donut) state.charts.donut.destroy();
  const ctx = elements.donutChartCanvas.getContext('2d');

  state.charts.donut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: shareData.labels || [],
      datasets: [{
        data: shareData.values || [],
        backgroundColor: TEA_PALETTE.colors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            font: { family: 'Plus Jakarta Sans', size: 9, weight: '600' },
            boxWidth: 10,
            padding: 8,
            color: '#334438'
          }
        },
        tooltip: {
          backgroundColor: '#1b4332',
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total ? ((ctx.raw / total) * 100).toFixed(1) : 0;
              return ` ${formatIndianCurrency(ctx.raw)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderRankingChart(rankingData) {
  if (state.charts.ranking) state.charts.ranking.destroy();
  const ctx = elements.rankingChartCanvas.getContext('2d');

  state.charts.ranking = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: rankingData.labels || [],
      datasets: [{
        label: 'Revenue (Rs.)',
        data: rankingData.values || [],
        backgroundColor: TEA_PALETTE.amber,
        borderRadius: 4,
        hoverBackgroundColor: TEA_PALETTE.copper,
        barThickness: 13,
        maxBarThickness: 15,
        barPercentage: 0.65,
        categoryPercentage: 0.75
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1b4332',
          callbacks: {
            label: (ctx) => ` Revenue: ${formatIndianCurrency(ctx.raw)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(226, 232, 228, 0.5)' },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 8.5 },
            color: '#647a6b',
            callback: (v) => formatChartAxisTick(v)
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 8.5, weight: '600' },
            color: '#16241b',
            padding: 4
          }
        }
      }
    }
  });
}

function renderChannelChart(channelData) {
  if (state.charts.channel) state.charts.channel.destroy();
  const ctx = elements.channelChartCanvas.getContext('2d');

  const shortLabels = (channelData.labels || []).map(lbl => {
    const s = String(lbl).trim();
    return s.length > 20 ? s.slice(0, 18) + '…' : s;
  });

  state.charts.channel = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: shortLabels,
      datasets: [{
        label: 'Revenue (Rs.)',
        data: channelData.values || [],
        backgroundColor: TEA_PALETTE.matcha,
        borderRadius: 5,
        hoverBackgroundColor: TEA_PALETTE.leaf,
        barThickness: 22,
        maxBarThickness: 28,
        barPercentage: 0.65,
        categoryPercentage: 0.75
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1b4332',
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              return channelData.labels[idx] || '';
            },
            label: (ctx) => ` Revenue: ${formatIndianCurrency(ctx.raw)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 8.5 },
            color: '#647a6b',
            maxRotation: 35,
            minRotation: 0,
            autoSkip: false
          }
        },
        y: {
          grid: { color: 'rgba(226, 232, 228, 0.5)' },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 9 },
            color: '#647a6b',
            callback: (v) => formatChartAxisTick(v)
          }
        }
      }
    }
  });
}


// ------------------------------------------------------------------------------
// MATRIX TABLE RENDERING
// ------------------------------------------------------------------------------
function renderMatrix(matrixData) {
  state.lastMatrixData = matrixData;
  elements.matrixTableTitle.textContent = matrixData.matrix_title || `${matrixData.classification_title || 'Commercial Performance'} Matrix`;

  const headers = elements.matrixDataTable.querySelectorAll('th');
  if (headers.length >= 5) {
    headers[0].textContent = matrixData.classification_title || 'Classification';
    headers[1].textContent = matrixData.volume_title || 'Volume (kgs)';
    headers[2].textContent = matrixData.revenue_title || 'Gross Auction Revenue (Rs.)';
    headers[3].textContent = matrixData.realization_title || 'Avg Realization (Rs. / kg)';
    headers[4].textContent = 'Share of Portfolio';
  }

  elements.matrixTableBody.innerHTML = '';
  (matrixData.rows || []).forEach(row => {
    let volDisplay = '';
    if (typeof row.volume === 'string' && row.volume.includes('kgs')) {
      volDisplay = escapeHtml(row.volume);
    } else {
      const numVol = parseFloat(row.volume) || 0.0;
      volDisplay = `${formatIndianNumber(numVol, 3)} kgs`;
    }

    let revDisplay = '';
    if (typeof row.revenue === 'string' && row.revenue.includes('Rs.')) {
      revDisplay = escapeHtml(row.revenue);
    } else {
      const numRev = parseFloat(row.revenue) || 0.0;
      revDisplay = formatIndianCurrency(numRev);
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(row.name)}</strong></td>
      <td>${volDisplay}</td>
      <td>${revDisplay}</td>
      <td>${escapeHtml(row.realization)}</td>
      <td><span class="share-pill">${row.share_pct}%</span></td>
    `;
    elements.matrixTableBody.appendChild(tr);
  });
}

// ------------------------------------------------------------------------------
// CURATED EXECUTIVE LOT LEDGER & SEARCH
// ------------------------------------------------------------------------------
function getCuratedColumns(firstRec) {
  const isBeta = state.client && state.client.client_id === 'client_beta';
  if (isBeta || ('PRODUCT_NAME' in firstRec || 'Product_Name' in firstRec)) {
    const cand = [
      { key: 'ORDER_ID', alt: 'Order_ID', label: 'Order Ref' },
      { key: 'PRODUCT_NAME', alt: 'Product_Name', label: 'Artisanal Product' },
      { key: 'CATEGORY', alt: 'Tea_Category', label: 'Category' },
      { key: 'SALES_CHANNEL', alt: 'Sales_Channel', label: 'Channel' },
      { key: 'UNITS_SOLD', alt: 'Volume_Sold_KG', label: 'Units Sold', isKg: true },
      { key: 'UNIT_PRICE_USD', alt: 'Unit_Price_INR', label: 'Price (Rs.)', isPrice: true },
      { key: 'NET_SALES_USD', alt: 'Gross_Revenue_INR', label: 'Net Sales (Rs.)', isCurr: true }
    ];
    return cand.map(c => {
      const actualKey = (c.key in firstRec) ? c.key : (c.alt in firstRec) ? c.alt : null;
      return actualKey ? { key: actualKey, label: c.label, isKg: c.isKg, isPrice: c.isPrice, isCurr: c.isCurr } : null;
    }).filter(Boolean);
  } else {
    const cand = [
      { key: 'LOT_ID', alt: 'INVNO', label: 'Invoice / Batch' },
      { key: 'ESTATE', alt: 'DESCN', label: 'Estate' },
      { key: 'SEASON_FLUSH', alt: 'SEASON', label: 'Season' },
      { key: 'TEA_GRADE', alt: 'GRADE', label: 'Grade' },
      { key: 'VOLUME_KG', alt: 'QTY', label: 'Volume (kgs)', isKg: true },
      { key: 'AVG_PRICE_USD', alt: 'RATE', label: 'Rate (Rs./kg)', isPrice: true },
      { key: 'TOTAL_REVENUE_USD', alt: 'INVOICE_AMOUNT', label: 'Valuation (Rs.)', isCurr: true }
    ];
    return cand.map(c => {
      const actualKey = (c.key in firstRec) ? c.key : (c.alt in firstRec) ? c.alt : null;
      return actualKey ? { key: actualKey, label: c.label, isKg: c.isKg, isPrice: c.isPrice, isCurr: c.isCurr } : null;
    }).filter(Boolean);
  }
}

function renderRawRecordsTable(records) {
  const cid = (state.client && state.client.client_id ? state.client.client_id : '').toLowerCase();
  const isAlpha = cid.includes('alpha');

  const ledgerTitle = document.getElementById('ledgerCardTitle');
  const ledgerSubtitle = document.getElementById('ledgerCardSubtitle');
  if (ledgerTitle) {
    ledgerTitle.textContent = isAlpha ? 'Audited Estate Auction Ledger' : 'Audited Specialty Retail Order Ledger';
  }
  if (ledgerSubtitle) {
    const domainDesc = isAlpha ? 'Darjeeling, Assam, Nilgiri & Dooars auction lots' : 'specialty retail batches';
    ledgerSubtitle.innerHTML = `Curated preview of verified records across ${domainDesc}. Full dataset available via <strong>📥 Export CSV</strong>.`;
  }

  if (!records || records.length === 0) {
    elements.rawTableHead.innerHTML = '<tr><th>No audited lots found</th></tr>';
    elements.rawTableBody.innerHTML = '';
    return;
  }

  let columns = getCuratedColumns(records[0]);
  if (columns.length === 0) {
    const rawKeys = Object.keys(records[0]).slice(0, 6);
    columns = rawKeys.map(k => ({ key: k, label: k.replace(/_/g, ' ') }));
  }

  elements.rawTableHead.innerHTML = '<tr>' + columns.map(c => `<th>${escapeHtml(c.label)}</th>`).join('') + '</tr>';

  // Sort by revenue column descending if available
  const revKey = (columns.find(c => c.isCurr) || {}).key || Object.keys(records[0])[0];
  const sorted = records.slice().sort((a, b) => (Number(b[revKey]) || 0) - (Number(a[revKey]) || 0));

  // Curated preview: top 10 key representative lots
  state.curatedRecords = sorted.slice(0, 10);
  fillRawTableRows(state.curatedRecords, columns);
}

function fillRawTableRows(records, columns) {
  elements.rawTableBody.innerHTML = '';
  if (!records || records.length === 0) {
    elements.rawTableBody.innerHTML = `<tr><td colspan="${columns.length}" style="text-align: center; color: var(--text-muted); padding: 14px;">No preview lots match keyword.</td></tr>`;
    return;
  }

  records.forEach(rec => {
    const tr = document.createElement('tr');
    tr.innerHTML = columns.map(colDef => {
      let val = rec[colDef.key];
      if (typeof val === 'number') {
        if (colDef.isCurr) {
          val = formatIndianCurrency(val);
        } else if (colDef.isKg) {
          val = `${formatIndianNumber(val, 3)} kgs`;
        } else if (colDef.isPrice) {
          val = `Rs. ${formatIndianNumber(val, 2)} / kg`;
        } else {
          val = Number.isInteger(val) ? formatIndianNumber(val, 0) : formatIndianNumber(val, 2);
        }
        return `<td>${val}</td>`;
      }
      return `<td>${escapeHtml(String(val ?? ''))}</td>`;
    }).join('');
    elements.rawTableBody.appendChild(tr);
  });
}

function filterRawRecordsTable() {
  const query = elements.recordSearchInput.value.toLowerCase().trim();
  if (!state.curatedRecords || state.curatedRecords.length === 0) return;

  const columns = getCuratedColumns(state.rawRecords[0] || {});
  if (!query) {
    fillRawTableRows(state.curatedRecords, columns);
    return;
  }

  const filtered = state.curatedRecords.filter(rec => {
    return columns.some(col => String(rec[col.key] ?? '').toLowerCase().includes(query));
  });
  fillRawTableRows(filtered, columns);
}

// ------------------------------------------------------------------------------
// EXPORT & EXECUTIVE BRIEFING
// ------------------------------------------------------------------------------
function exportFilteredData() {
  const query = buildSlicerQuery();
  window.open(`/api/reports/export?${query}&token=${encodeURIComponent(state.token)}`, '_blank');
}

function exportMatrixData() {
  const query = buildSlicerQuery();
  window.open(`/api/reports/export_matrix?${query}&token=${encodeURIComponent(state.token)}`, '_blank');
}

// ==============================================================================
// ERP HEALTH TELEMETRY & DIAGNOSTICS MODAL
// ==============================================================================
async function updateErpHealthPill() {
  if (elements.erpHealthPill) {
    elements.erpHealthPill.style.display = 'none';
  }
}

async function openExecutiveBriefing() {
  elements.briefingModal.classList.add('active');
  elements.briefingContentPlaceholder.innerHTML = `
    <div style="padding: 24px 0; text-align: center; color: var(--tea-forest);">
      <span class="client-chip-dot"></span> Synthesizing executive briefing from filtered ledger...
    </div>
  `;

  const query = buildSlicerQuery();
  try {
    const res = await fetch(`/api/reports/briefing?${query}`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    const data = await res.json();

    if (!res.ok) {
      elements.briefingContentPlaceholder.innerHTML = `<div style="color: var(--tea-terracotta);">${data.detail || 'Error loading briefing.'}</div>`;
      return;
    }

    state.lastBriefingData = data;
    renderBriefingModalContent(data);
  } catch (e) {
    elements.briefingContentPlaceholder.innerHTML = `<div style="color: var(--tea-terracotta);">Failed to connect to briefing service.</div>`;
  }
}

function renderBriefingModalContent(data) {
  elements.briefingContentPlaceholder.innerHTML = `
    <div class="narrative-card">
      <div class="narrative-section">
        <div class="narrative-tag answer"><span>Executive Overview</span></div>
        <div class="narrative-answer" style="font-size: 0.88rem; line-height: 1.5;">${formatRichText(data.executive_summary || '')}</div>
      </div>
      
      <div class="narrative-section">
        <div class="narrative-tag evidence"><span>Macro Commercial Drivers</span></div>
        <ul class="narrative-evidence-list">
          ${(data.macro_drivers || []).map(d => `<li style="font-size: 0.84rem; line-height: 1.45;">${formatRichText(d)}</li>`).join('')}
        </ul>
      </div>
      
      <div class="narrative-section">
        <div class="narrative-tag why"><span>Root Cause & Terroir Variance</span></div>
        <div class="narrative-why" style="font-size: 0.82rem; line-height: 1.45;">${formatRichText(data.root_cause_variance || '')}</div>
      </div>
      
      <div class="narrative-section">
        <div class="narrative-tag action"><span>Board-Level Strategic Directives</span></div>
        <div class="narrative-action" style="font-size: 0.82rem; line-height: 1.45;">${formatRichText(data.strategic_directives || '')}</div>
      </div>
    </div>
  `;
}

// ------------------------------------------------------------------------------
// CUSTOMIZED EXECUTIVE DOSSIER (Full Report + User Session Inquiries)
// ------------------------------------------------------------------------------
async function openCustomDossier() {
  if (!elements.customDossierModal) return;
  elements.customDossierModal.classList.add('active');

  const clientName = state.client ? state.client.client_name : 'Tea Enterprise';
  const activeSlicersList = [];
  if (state.slicersConfig) {
    state.slicersConfig.forEach(s => {
      const v = state.filters[s.key];
      if (v && !v.includes('All') && v.length > 0) {
        activeSlicersList.push(`${s.label}: ${v.join(', ')}`);
      }
    });
  }
  const scopeText = activeSlicersList.length > 0 ? activeSlicersList.join(' | ') : 'Complete Ledger (All Slicers)';
  elements.dossierSubtitle.textContent = `Client: ${clientName} • Scope: ${scopeText}`;

  elements.dossierModalBody.innerHTML = `
    <div style="text-align: center; padding: 40px; color: var(--tea-forest);">
      <span class="client-chip-dot"></span> Compiling active ledger metrics, matrix, and session inquiries...
    </div>
  `;

  // Ensure fresh briefing is loaded
  const query = buildSlicerQuery();
  let briefingData = state.lastBriefingData;
  try {
    const res = await fetch(`/api/reports/briefing?${query}`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (res.ok) {
      briefingData = await res.json();
      state.lastBriefingData = briefingData;
    }
  } catch (e) {
    console.warn('Briefing fetch note:', e);
  }

  renderCustomDossierBody(briefingData);
}

function renderCustomDossierBody(briefing) {
  const clientName = state.client ? state.client.client_name : 'Tea Enterprise';
  const nowStr = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
  const activeSlicersList = [];
  if (state.slicersConfig) {
    state.slicersConfig.forEach(s => {
      const v = state.filters[s.key];
      if (v && !v.includes('All') && v.length > 0) {
        activeSlicersList.push(`${s.label}: ${v.join(', ')}`);
      }
    });
  }
  const filterScope = activeSlicersList.length > 0 ? activeSlicersList.join(' • ') : 'Complete Ledger (All Slicers)';

  // 1. KPI Scorecard Tiles
  const kpiData = state.lastKpiData ? state.lastKpiData.kpis : {
    revenue: { label: 'Gross Revenue', value: 'Rs. 0.00' },
    volume: { label: 'Volume Sold', value: '0.000 kgs' },
    realization: { label: 'Avg Realization', value: 'Rs. 0.00 / kg' },
    quality: { label: 'Quality Score', value: '0.0 / 100' }
  };

  const kpisHtml = `
    <div class="dossier-kpi-grid">
      <div class="dossier-kpi-item">
        <div class="dossier-kpi-label">${escapeHtml(kpiData.revenue.label)}</div>
        <div class="dossier-kpi-val">${escapeHtml(kpiData.revenue.value)}</div>
      </div>
      <div class="dossier-kpi-item">
        <div class="dossier-kpi-label">${escapeHtml(kpiData.volume.label)}</div>
        <div class="dossier-kpi-val">${escapeHtml(kpiData.volume.value)}</div>
      </div>
      <div class="dossier-kpi-item">
        <div class="dossier-kpi-label">${escapeHtml(kpiData.realization.label)}</div>
        <div class="dossier-kpi-val">${escapeHtml(kpiData.realization.value)}</div>
      </div>
      <div class="dossier-kpi-item">
        <div class="dossier-kpi-label">${escapeHtml(kpiData.quality.label)}</div>
        <div class="dossier-kpi-val">${escapeHtml(kpiData.quality.value)}</div>
      </div>
      ${kpiData.custom ? `
      <div class="dossier-kpi-item">
        <div class="dossier-kpi-label">${escapeHtml(kpiData.custom.label)}</div>
        <div class="dossier-kpi-val">${escapeHtml(kpiData.custom.value)}</div>
      </div>` : ''}
    </div>
  `;

  // 2. Executive Management Briefing Section
  const bData = briefing || state.lastBriefingData || {
    executive_summary: 'Audited commercial operations indicate sustained execution across primary certified grades.',
    macro_drivers: ['Verified auction hammer clearance across primary certified regions.', 'Volume realization aligned with top-tier international quality benchmarks.'],
    root_cause_variance: 'Commercial performance is anchored in harvest flush seasonality and elevation microclimates.',
    strategic_directives: 'Channel upcoming harvest lots into private-treaty export auctions to capture international buyer margins.'
  };

  const briefingHtml = `
    <div class="dossier-section-card">
      <div class="dossier-section-title">
        <span>📄</span>
        <span>Audited Executive Management Briefing</span>
      </div>
      <div class="narrative-card">
        <div class="narrative-section">
          <div class="narrative-tag answer"><span>Executive Overview</span></div>
          <div class="narrative-answer" style="font-size: 0.84rem; line-height: 1.45;">${formatRichText(bData.executive_summary || '')}</div>
        </div>
        <div class="narrative-section">
          <div class="narrative-tag evidence"><span>Primary Commercial Drivers</span></div>
          <ul class="narrative-evidence-list">
            ${(bData.macro_drivers || []).map(d => `<li style="font-size: 0.82rem;">${formatRichText(d)}</li>`).join('')}
          </ul>
        </div>
        <div class="narrative-section">
          <div class="narrative-tag why"><span>Root Cause & Terroir Variance</span></div>
          <div class="narrative-why" style="font-size: 0.80rem;">${formatRichText(bData.root_cause_variance || '')}</div>
        </div>
        <div class="narrative-section">
          <div class="narrative-tag action"><span>Board-Level Strategic Directives</span></div>
          <div class="narrative-action" style="font-size: 0.80rem;">${formatRichText(bData.strategic_directives || '')}</div>
        </div>
      </div>
    </div>
  `;

  // 3. Commercial Performance Matrix Table Snapshot
  let matrixRowsHtml = '';
  if (state.lastMatrixData && state.lastMatrixData.rows && state.lastMatrixData.rows.length > 0) {
    matrixRowsHtml = state.lastMatrixData.rows.map(r => `
      <tr>
        <td style="padding: 6px 10px;"><strong>${escapeHtml(r.name)}</strong></td>
        <td style="padding: 6px 10px;">${escapeHtml(r.volume)}</td>
        <td style="padding: 6px 10px;">${escapeHtml(r.revenue)}</td>
        <td style="padding: 6px 10px;">${escapeHtml(r.realization)}</td>
        <td style="padding: 6px 10px;"><span class="share-pill">${r.share_pct}%</span></td>
      </tr>
    `).join('');
  }

  const matrixHtml = matrixRowsHtml ? `
    <div class="dossier-section-card">
      <div class="dossier-section-title">
        <span>📋</span>
        <span>Commercial Performance Matrix Snapshot</span>
      </div>
      <div class="table-responsive">
        <table class="matrix-table" style="margin-top: 4px; font-size: 0.78rem;">
          <thead>
            <tr>
              <th style="padding: 6px 10px;">Classification</th>
              <th style="padding: 6px 10px;">Volume</th>
              <th style="padding: 6px 10px;">Gross Value</th>
              <th style="padding: 6px 10px;">Realization</th>
              <th style="padding: 6px 10px;">Share</th>
            </tr>
          </thead>
          <tbody>
            ${matrixRowsHtml}
          </tbody>
        </table>
      </div>
    </div>
  ` : '';

  // 4. User Customized Chat Inquiries Section
  let chatSectionHtml = '';
  const dossierChartInstances = [];

  if (state.chatHistory && state.chatHistory.length > 0) {
    const cards = state.chatHistory.map((item, idx) => {
      let inquiryChartHtml = '';
      if (item.chart_data && item.chart_data.labels && item.chart_data.labels.length >= 2) {
        const canvasId = `dossier_canvas_${idx}_` + Math.random().toString(36).substring(2, 7);
        const maxVal = Math.max(...item.chart_data.values, 0.001);
        const isDonut = item.chart_data.type === 'donut';

        const barsHtml = item.chart_data.labels.map((lbl, i) => {
          const val = item.chart_data.values[i];
          const pct = Math.min(100, Math.max(4, (val / maxVal) * 100));
          const color = TEA_PALETTE.colors[i % TEA_PALETTE.colors.length];
          const formattedVal = formatIndianCurrency(val);
          return `
            <div class="dossier-bar-row">
              <span class="dossier-bar-label" title="${escapeHtml(lbl)}">${escapeHtml(lbl)}</span>
              <div class="dossier-bar-track">
                <div class="dossier-bar-fill" style="width: ${pct.toFixed(1)}%; background: ${color};"></div>
              </div>
              <span class="dossier-bar-val">${formattedVal}</span>
            </div>
          `;
        }).join('');

        inquiryChartHtml = `
          <div class="dossier-inquiry-chart-block">
            <div class="dossier-chart-header">
              <span class="dossier-chart-tag">📊 ${escapeHtml(item.chart_data.title || 'Visual Distribution')}</span>
            </div>
            <div class="dossier-chart-canvas-wrap" style="height: 125px; position: relative; margin-bottom: 8px;">
              <canvas id="${canvasId}"></canvas>
            </div>
            <div class="dossier-bars-container">
              ${barsHtml}
            </div>
          </div>
        `;

        dossierChartInstances.push({
          id: canvasId,
          chartData: item.chart_data,
          isDonut: isDonut
        });
      }

      return `
        <div class="dossier-inquiry-card">
          <div class="dossier-inquiry-q">
            <span>💬</span>
            <span>Inquiry #${idx + 1}: &ldquo;${escapeHtml(item.question)}&rdquo;</span>
            <span style="font-size: 0.70rem; color: var(--text-muted); font-weight: normal; margin-left: auto;">${escapeHtml(item.timestamp)}</span>
          </div>
          <div class="dossier-inquiry-a">${formatRichText(item.answer)}</div>
          ${inquiryChartHtml}
          ${(item.key_insights || item.recommendations) ? `
            <div class="dossier-inquiry-meta">
              ${item.key_insights ? `<div><strong>Insight:</strong> ${formatRichText(item.key_insights)}</div>` : ''}
              ${item.recommendations ? `<div><strong>Recommendation:</strong> ${formatRichText(item.recommendations)}</div>` : ''}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    chatSectionHtml = `
      <div class="dossier-section-card">
        <div class="dossier-section-title">
          <span>✨</span>
          <span>Customized Inquiries & AI Analyst Findings (${state.chatHistory.length})</span>
        </div>
        ${cards}
      </div>
    `;
  } else {
    chatSectionHtml = `
      <div class="dossier-section-card">
        <div class="dossier-section-title">
          <span>✨</span>
          <span>Customized Inquiries & AI Analyst Findings</span>
        </div>
        <div class="dossier-empty-note">
          💡 No ad-hoc inquiries recorded in this active session. Any questions you ask the AI Business Analyst in the Chat tab will automatically be captured and embedded into your personalized executive dossier.
        </div>
      </div>
    `;
  }

  // Assemble Complete Dossier
  elements.dossierModalBody.innerHTML = `
    <!-- Header Banner -->
    <div class="dossier-header-panel">
      <div class="dossier-brand-sub">🍵 Camellia Atelier & Intelligence • Audited Executive Dossier</div>
      <h1 class="dossier-main-title">${escapeHtml(clientName)}</h1>
      <div class="dossier-meta-row">
        <div class="dossier-meta-item">Scope: <strong>${escapeHtml(filterScope)}</strong></div>
        <div class="dossier-meta-item">Date: <strong>${escapeHtml(nowStr)}</strong></div>
        <div class="dossier-meta-item">Status: <strong>Audited & Certified</strong></div>
      </div>
    </div>

    <!-- 1. KPI Scorecard -->
    ${kpisHtml}

    <!-- 2. Grounded Executive Briefing -->
    ${briefingHtml}

    <!-- 3. Matrix Summary -->
    ${matrixHtml}

    <!-- 4. Session Q&A Customization -->
    ${chatSectionHtml}
  `;

  // Destroy previous dossier Chart instances if any
  if (state.dossierChartObjects) {
    state.dossierChartObjects.forEach(c => { try { c.destroy(); } catch (e) {} });
  }
  state.dossierChartObjects = [];

  // Initialize Chart.js for all inquiry canvases
  dossierChartInstances.forEach(item => {
    const canvas = document.getElementById(item.id);
    if (canvas && window.Chart) {
      try {
        const chartInst = new Chart(canvas, {
          type: item.isDonut ? 'doughnut' : 'bar',
          data: {
            labels: item.chartData.labels,
            datasets: [{
              data: item.chartData.values,
              backgroundColor: item.isDonut ? TEA_PALETTE.colors : '#2d6a4f',
              borderRadius: item.isDonut ? 0 : 4,
              barThickness: 18,
              maxBarThickness: 24,
              barPercentage: 0.75
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: item.isDonut, position: 'right', labels: { boxWidth: 9, font: { size: 9 } } },
              tooltip: {
                callbacks: {
                  label: function(ctx) {
                    return ' ' + formatIndianCurrency(ctx.raw);
                  }
                }
              }
            },
            scales: item.isDonut ? {} : {
              x: { ticks: { font: { size: 8.5 }, maxRotation: 20 } },
              y: { ticks: { font: { size: 8.5 }, callback: v => formatChartAxisTick(v) } }
            }
          }
        });
        state.dossierChartObjects.push(chartInst);
      } catch (err) {
        console.warn('Dossier inquiry chart render note:', err);
      }
    }
  });
}

function printCustomDossier() {
  window.print();
}

function downloadHtmlDossier() {
  if (!elements.dossierModalBody) return;
  const content = elements.dossierModalBody.innerHTML;
  const clientName = state.client ? state.client.client_name : 'Tea_Enterprise';
  const cleanClient = clientName.replace(/[^a-zA-Z0-9]/g, '_');
  const dateStr = new Date().toISOString().split('T')[0];

  const htmlDocument = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Executive Intelligence Dossier - ${escapeHtml(clientName)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
  <style>
    :root {
      --tea-forest: #1b4332;
      --tea-leaf: #2d6a4f;
      --tea-matcha: #40916c;
      --tea-sage: #52b788;
      --tea-amber: #c58f3b;
      --tea-terracotta: #b2533e;
      --bg-parchment: #f9f7f2;
      --bg-cream: #f4f1ea;
      --border-light: #e2e8e4;
      --text-dark: #16241b;
      --text-body: #334438;
      --text-muted: #647a6b;
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-serif: 'Playfair Display', Georgia, serif;
    }
    body {
      font-family: var(--font-sans);
      background: #fbfaf7;
      color: var(--text-body);
      margin: 0;
      padding: 30px;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .dossier-header-panel {
      background: #ffffff;
      border: 1px solid var(--border-light);
      border-radius: 8px;
      padding: 18px 24px;
      border-left: 5px solid var(--tea-forest);
    }
    .dossier-brand-sub { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--tea-leaf); margin-bottom: 4px; }
    .dossier-main-title { font-family: var(--font-serif); font-size: 1.4rem; color: var(--tea-forest); margin: 0 0 6px 0; }
    .dossier-meta-row { display: flex; gap: 16px; font-size: 0.78rem; color: var(--text-muted); }
    .dossier-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .dossier-kpi-item { background: #ffffff; border: 1px solid var(--border-light); border-radius: 6px; padding: 10px 14px; }
    .dossier-kpi-label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 3px; }
    .dossier-kpi-val { font-size: 1.2rem; font-weight: 800; color: var(--tea-forest); }
    .dossier-section-card { background: #ffffff; border: 1px solid var(--border-light); border-radius: 8px; padding: 18px 20px; }
    .dossier-section-title { font-size: 0.95rem; font-weight: 700; color: var(--tea-forest); margin-bottom: 10px; border-bottom: 1px solid var(--border-light); padding-bottom: 6px; }
    .narrative-card { display: flex; flex-direction: column; gap: 8px; }
    .narrative-tag { font-size: 0.68rem; font-weight: 800; text-transform: uppercase; padding: 2px 7px; border-radius: 4px; display: inline-block; margin-bottom: 4px; }
    .narrative-tag.answer { background: #e8f5ee; color: var(--tea-forest); }
    .narrative-tag.evidence { background: #fff8eb; color: #92400e; }
    .narrative-tag.why { background: #f4f1ea; color: #495e50; }
    .narrative-tag.action { background: #e6f4ea; color: #137333; }
    .narrative-evidence-list { list-style: none; padding-left: 0; margin: 4px 0 0 0; }
    .narrative-evidence-list li { margin-bottom: 4px; }
    .matrix-table { width: 100%; border-collapse: collapse; }
    .matrix-table th { background: var(--bg-parchment); color: var(--tea-forest); font-size: 0.72rem; padding: 8px 10px; text-align: left; }
    .matrix-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-light); }
    .share-pill { background: #e8f5ee; color: var(--tea-forest); padding: 2px 6px; border-radius: 12px; font-weight: 700; }
    .dossier-inquiry-card { background: #fbfaf7; border: 1px solid var(--border-light); border-radius: 6px; padding: 12px 14px; margin-bottom: 10px; border-left: 3px solid var(--tea-leaf); }
    .dossier-inquiry-q { font-size: 0.84rem; font-weight: 700; color: var(--tea-forest); margin-bottom: 4px; }
    .dossier-inquiry-a { font-size: 0.80rem; line-height: 1.45; color: var(--text-dark); margin-bottom: 6px; }
    .dossier-inquiry-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.74rem; background: #ffffff; padding: 8px 10px; border-radius: 4px; border: 1px solid var(--border-light); }
    .dossier-inquiry-chart-block { background: #ffffff; border: 1px solid var(--border-light); border-radius: 6px; padding: 10px 14px; margin: 10px 0; }
    .dossier-chart-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
    .dossier-chart-tag { font-size: 0.70rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--tea-leaf); }
    .dossier-chart-canvas-wrap { display: none; }
    .dossier-bars-container { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
    .dossier-bar-row { display: grid; grid-template-columns: 140px 1fr 110px; align-items: center; gap: 10px; font-size: 0.73rem; }
    .dossier-bar-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-dark); font-weight: 600; }
    .dossier-bar-track { background: #f0ede6; border-radius: 3px; height: 7px; width: 100%; overflow: hidden; position: relative; }
    .dossier-bar-fill { height: 100%; border-radius: 3px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .dossier-bar-val { text-align: right; font-weight: 700; color: var(--tea-forest); font-variant-numeric: tabular-nums; white-space: nowrap; }
  </style>
</head>
<body>
  <div class="container">
    ${content}
  </div>
</body>
</html>`;

  const blob = new Blob([htmlDocument], { type: 'text/html;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Executive_Dossier_${cleanClient}_${dateStr}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ------------------------------------------------------------------------------
// UTILITIES
// ------------------------------------------------------------------------------
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatRichText(str) {
  if (str === null || str === undefined) return '';
  const escaped = escapeHtml(str);
  const bolded = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  return bolded
    .replace(/\r\n/g, '\n')
    .replace(/\n\n+/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

// ------------------------------------------------------------------------------
// DYNAMIC WINDOW RESIZE & LAYOUT RECALCULATION
// ------------------------------------------------------------------------------
let resizeDebounceTimer = null;
window.addEventListener('resize', () => {
  if (resizeDebounceTimer) clearTimeout(resizeDebounceTimer);
  resizeDebounceTimer = setTimeout(() => {
    // Force Chart.js to recalculate dimensions to current responsive container bounds
    if (state.charts) {
      Object.values(state.charts).forEach(chart => {
        if (chart && typeof chart.resize === 'function') {
          chart.resize();
        }
      });
    }
  }, 100);
});

