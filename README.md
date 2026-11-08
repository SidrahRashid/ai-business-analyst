# Camellia AI Business Analyst & Executive Intelligence Terminal
**Enterprise AI Business Analyst & Power BI Intelligence Portal powered by DuckDB OLAP & Google Gemini AI.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-FFF000.svg?style=flat&logo=duckdb&logoColor=black)](https://duckdb.org)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://aistudio.google.com/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🌐 **Live Public Application:** [https://ai-business-analyst-amuj.onrender.com](https://ai-business-analyst-amuj.onrender.com)  
> 🔑 **1-Click Demo Login:** `client_alpha` or `client_beta` | **Password:** `password123`

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
├── Procfile                    # Cloud platform process launcher (Render / Railway)
├── requirements.txt            # Python dependencies
├── run.bat                     # Single-click Windows server launcher
├── .env.example                # Sample environment variables template
├── .gitignore                  # Git privacy & cache exclusions
└── README.md                   # System documentation
```

---

## 3. Quickstart: Local Setup

### Prerequisites
* Python 3.10+ (Python 3.12 recommended)
* A Google Gemini API key (Free tier from [Google AI Studio](https://aistudio.google.com/)) or OpenAI API key.

### 1. Environment Setup
Create a `.env` file from the provided `.env.example`:
```bash
cp .env.example .env
```
Open `.env` and insert your Gemini API key:
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

### 3. Launch Local Server

**One-Click (Windows):**
```cmd
run.bat
```

**Terminal:**
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

*Default password for both accounts:* **`password123`** *(or click the demo card on the login screen)*

---


