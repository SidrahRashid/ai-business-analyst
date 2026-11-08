# Camellia AI Business Analyst & Executive Intelligence Terminal
**Enterprise AI Business Analyst & Power BI Intelligence Portal powered by DuckDB OLAP & Google Gemini AI.**

---

## 1. Executive System Overview

The **Camellia AI Business Analyst** is an executive-grade, real-data intelligence platform designed for C-suite directors, plantation operators, and commercial retail managers in the enterprise tea trade.

It pairs a high-speed **FastAPI** backend and **DuckDB OLAP Engine** with a bespoke **Vanilla JS/Glassmorphism Power BI Executive Dashboard**, delivering sub-second analytics, star-schema aggregations, and live AI executive insights.

### Core Capabilities:
* **Zero Data Exfiltration Privacy Model:** Raw transaction ledgers remain strictly inside the local in-memory columnar engine. Only aggregated high-level summary facts are passed to the LLM for narrative generation.
* **100% Deterministic Calculations:** Mathematical aggregations, weighted averages, and rankings are calculated by DuckDB and Pandas. The AI never fabricates numbers or performs arithmetic.
* **Embedded Star-Schema OLAP (DuckDB):** Performs out-of-core, zero-copy joins across dimension and fact tables in sub-millisecond speeds with minimal RAM footprint.
* **Two Multi-Tenant Demo Portals:**
  - **🍵 Himalayan Estate Teas & Auctions (`client_alpha`):** Darjeeling & Assam plantation lots, auction hammer realizations, regional terroir, and export shipments.
  - **🍃 Zenith Artisanal Blends & Retail (`client_beta`):** Specialty tea retail, Matcha & Oolong blends, packaging formats, and omnichannel margins.
* **Live AI Intelligence (Google Gemini `gemini-2.5-flash`):** Synthesizes grounded executive answers, board-level strategic briefings, and multi-turn conversational follow-ups.
* **Power BI Standard Executive Dashboard:** Dynamic multi-select slicers, single-line KPI summary tiles, Commercial Matrix with live sort/export, and curated lot ledger.
* **Customized Executive Dossier:** Instant board-ready strategic synthesis with chat inquiry tracking and print-ready PDF/HTML layout.

---

## 2. Directory Structure

```
ai-business-analyst/
├── data/                       # Multi-tenant Star Schema datasets & caches
│   ├── client_alpha/           # Dim & Fact CSVs for Tea Auctions
│   ├── client_beta/            # Dim & Fact CSVs for Specialty Retail
│   ├── cache/                  # Multi-worker shared cache & DuckDB spill dir
│   └── glossary/               # Dynamic business jargon definitions
│
├── docs/                       # Documentation, roadmaps, and executive reports
│   ├── ENTERPRISE_ROADMAP.md   # Architectural roadmap
│   ├── walkthrough.md          # End-to-end user walkthrough
│   ├── generate_authority_report.py
│   └── Project_Authority_Report_AI_Business_Analyst.docx
│
├── scripts/                    # Data preparation & table generation
│   └── create_relational_tables.py
│
├── static/                     # Clean Vanilla JS frontend
│   ├── index.html              # Single-page Power BI dashboard & chat UI
│   ├── app.js                  # Dynamic slicer, chart, and dossier controller
│   ├── style.css               # Editorial Pinterest & glassmorphic aesthetics
│   └── assets/                 # Brand imagery and visuals
│
├── tests/                      # Automated test suite
│   ├── test_tea_server.py      # 11-step end-to-end integration tests
│   ├── test_api_upgrades.py    # Architecture & glossary endpoint tests
│   ├── test_overcome_limitations.py # DuckDB OLAP & window function validation
│   ├── verify_briefing.py      # Grounded executive briefing verification
│   ├── verify_chat_fixes.py    # Bounds, benchmark, and ranking checks
│   └── verify_multiselect.py   # Multi-select slicer verification
│
├── server.py                   # FastAPI backend application entrypoint
├── app.py                      # Alternative Streamlit client portal
├── analytics_engine.py         # AI analysis planner & deterministic math engine
├── olap_engine.py              # DuckDB OLAP & lazy star-schema join engine
├── clients_config.py           # Multi-tenant authentication & access registry
├── complex_analytics.py        # Anomaly detection, Pareto & statistical models
├── cache_provider.py           # Multi-worker shared file/in-memory cache
├── glossary_manager.py         # Dynamic business jargon & formula dictionary
│
├── requirements.txt            # Python dependencies
├── run.bat                     # Single-click Windows server launcher
├── .env.example                # Sample environment variables template
├── .gitignore                  # Git privacy & cache exclusions
└── README.md                   # System documentation
```

---

## 3. Quickstart & Running the Application

### Prerequisites
* Python 3.10+ (Python 3.12 recommended)
* A Google Gemini API key (free from [Google AI Studio](https://aistudio.google.com/)) or OpenAI API key.

### 1. Environment Setup
Create a `.env` file in the root directory from `.env.example`:
```bash
cp .env.example .env
```
Add your Gemini or OpenAI API key inside `.env`:
```env
GEMINI_API_KEY=AIzaSy...
```

### 2. Install Dependencies
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Launch the Server

**Option A: One-Click Launch (Windows)**
```cmd
run.bat
```

**Option B: Manual Launch**
```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## 4. Pre-Configured Enterprise Demo Accounts

| Client ID | Display Name | Industry Domain | Data Scope |
| :--- | :--- | :--- | :--- |
| **`client_alpha`** | **Himalayan Estate Teas & Auctions** | Darjeeling, Assam & Nilgiri Auction Lots | 4,800 Audited Lots |
| **`client_beta`** | **Zenith Artisanal Blends & Retail** | D2C Specialty Blends & Global Boutiques | 4,800 Sales Orders |

*Default password for both demo accounts:* **`password123`** *(or click the 1-click login card on the login screen)*

---

## 5. Running Automated Verification Suites

Execute tests with your active environment:
```powershell
python tests/test_tea_server.py
python tests/test_overcome_limitations.py
python tests/test_api_upgrades.py
python tests/verify_multiselect.py
python tests/verify_briefing.py
python tests/verify_chat_fixes.py
```

---

## 6. How to Upload This Project to GitHub

Follow these exact steps to push this project to a new GitHub repository securely:

### Step 1: Ensure Secrets & Caches are Excluded
Check that `.env` is ignored and only `.env.example` will be tracked:
```powershell
git status --ignored
```
*(Verify `.env` and `.venv/` appear under Untracked / Ignored files)*

### Step 2: Initialize Git Repository
```powershell
git init
git branch -M main
```

### Step 3: Stage and Commit the Code
```powershell
git add .
git status
```
Confirm that:
* ✅ `.env` is **NOT** listed.
* ✅ `.venv/` is **NOT** listed.
* ✅ `data/cache/` is **NOT** listed.

Commit the files:
```powershell
git commit -m "Initial commit: Camellia AI Business Analyst & Executive Intelligence Terminal"
```

### Step 4: Link Your GitHub Repository and Push
1. Create a new repository on [GitHub](https://github.com/new) (e.g. `ai-business-analyst`), leave it empty (without initializing README/license).
2. Run the following commands (replace `<YOUR_USERNAME>` with your GitHub username):
```powershell
git remote add origin https://github.com/<YOUR_USERNAME>/ai-business-analyst.git
git push -u origin main
```

---

## 7. Executive Intelligence Dossier & Dual Exports

1. **📥 Export Matrix CSV (`/api/reports/export_matrix`):** Exports the aggregated **Commercial Performance Matrix** matching currently active slicers and displayed columns.
2. **📥 Export Ledger CSV (`/api/reports/export`):** Streams the curated transaction ledger directly to Excel matching active filters.
3. **📑 Executive Intelligence Dossier:** One-click board-ready executive report with print-to-PDF formatting and live Q&A summaries.

---

## 8. Strategic Enterprise Roadmap

See [docs/ENTERPRISE_ROADMAP.md](docs/ENTERPRISE_ROADMAP.md) for the strategic plan, including:
* **Pillar 1:** Predictive & Prescriptive Scenario Modeling (Interactive "What-If" Sandbox)
* **Pillar 2:** Executive Delivery (Automated 8:00 AM WhatsApp/Email Briefings, Server-Side Vector PDFs)
* **Pillar 3:** Enterprise Scaling (Change Data Capture [CDC], Multi-Tenant RBAC Governance)
* **Pillar 4:** Plantation Agricultural Supply Chain Expansion (Green Leaf Outturn %)
