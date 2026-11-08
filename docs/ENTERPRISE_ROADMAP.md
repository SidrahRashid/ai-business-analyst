# AI Business Analyst — Enterprise Roadmap & Strategic Decision Memo
**Project:** Camellia AI Business Analyst & Executive Intelligence Terminal  
**Updated:** 2026-11-08 | **Review Horizon:** Q4 2026 – Q2 2027  
**Workspace:** `ai-business-analyst`  
**Live Application:** `http://127.0.0.1:8000`

---

## 1. System Foundations & Current Live State

| Component | Status | Operational Capability |
| :--- | :---: | :--- |
| **Embedded DuckDB OLAP Engine** | ✅ Active | High-performance, in-process columnar database with zero-copy star-schema relational joins. Sub-millisecond aggregations on multi-thousand row ledgers. |
| **Dynamic Multi-Tenant Discovery** | ✅ Active | Auto-discovers tenant directories (`data/client_*`), auto-detects date/numeric metrics and categorical slicers with zero hardcoded column assumptions. |
| **100% Deterministic Calculations** | ✅ Active | Mathematical aggregations, weighted averages, and rankings computed deterministically via DuckDB and Pandas. Zero AI hallucination of metrics. |
| **Grounded AI Briefings & Narratives** | ✅ Active | Google Gemini (`gemini-2.5-flash`) live synthesis delivering executive management briefings with verified bold numbers, macro drivers, and strategic directives. |
| **Power BI Executive Terminal** | ✅ Active | Dynamic multi-select slicers, single-line 5 KPI summary row, Commercial Matrix with live sort/export, and curated Lot Reference ledger. |
| **Multi-Worker Shared Cache** | ✅ Active | File-backed shared cache (`data/cache/`) persisting schemas, synonyms, and DuckDB temp spills across multi-process server workers. |

---

## 2. Pillar 1: Predictive & Prescriptive Intelligence (Beyond Descriptive Data)
*Currently, the system provides top-tier Descriptive Analytics ("What happened?"). The next competitive edge is Predictive & Prescriptive Modeling:*

### 1.1 Interactive "What-If" Scenario Simulator (Executive Sandbox)
* **Goal:** Allow directors and strategy leaders to simulate market scenarios via natural language or UI sliders.
* **Example Prompts:**
  * *"What if the average auction realization for First Flush drops by 8%?"*
  * *"What if we divert 20% of plantation production into high-value Orthodox specialty?"*
  * *"What if shipping freight costs increase by 15% across European export channels?"*
* **Engine Action:** Recalculates projected gross revenue, margin impact, and displays a side-by-side variance analysis with recommended operational hedges.

### 1.2 Proactive Leakage & Anomaly Detection (Autonomous Watchdog)
* **Goal:** Instead of waiting for ad-hoc user queries, run an automated background scan that alerts leadership to:
  * **Price Realization Depressions:** E.g., lots realizing significantly below the estate's historical 30-day baseline.
  * **Tare Weight & Packing Discrepancies:** Outliers in container tare or net packed weight variances across factory lines.
  * **Unsold / Stagnant Lots:** Invoices packed but un-despatched beyond standard turnaround thresholds.

### 1.3 Channel Arbitrage Engine (Auction vs. Private Contract)
* **Goal:** Compare price realization spreads between **Primary Auction Clearances** and **Direct Private / Export Saudas** per grade.
* **Prescriptive Directive:** Advise factory managers which sales channel yields the highest net realization for upcoming manufactured batches.

---

## 3. Pillar 2: Executive Delivery & Automation
*Executives often prefer concise intelligence pushed directly to their channels rather than logging into a web terminal:*

### 2.1 Automated Daily Executive Dispatch (Email / WhatsApp / Telegram)
* **Scheduled 8:00 AM Dispatch:** Pushed directly to C-suite mobile devices.
* **Gemini Executive Synthesis:** 4 concise bullet points summarizing yesterday's packed volume, top-performing estate, auction price realization, and flagged anomalies.

### 2.2 Pixel-Perfect Server-Side PDF Dossiers (Boardroom Ready)
* **Implementation:** Server-side PDF generation using `ReportLab` or `WeasyPrint`.
* **Output:** Official company letterhead, high-resolution vector charts, executive signatures, and audit stamps at the click of a button.

### 2.3 Hands-Free Executive Voice Mode
* **Ambient Audio Assistant (Speech-to-Speech):** Hands-free conversational interface for directors reviewing estate metrics while commuting or in meetings.

---

## 4. Pillar 3: Data Architecture & Enterprise Scaling
*Scaling the architecture from local multi-tenant star schemas to multi-terabyte data lakehouses:*

### 3.1 Incremental Delta Sync (Change Data Capture - CDC)
* Connect to production warehouse/lakehouse sources (BigQuery, Snowflake, Databricks, PostgreSQL) with incremental CDC sync.
* Persists historical snapshots into an embedded local **DuckDB / Parquet Lakehouse** for sub-millisecond warm queries and offline resilience.

### 3.2 Role-Based Access Control (RBAC) & Enterprise SSO
* **Garden Factory Managers:** Access restricted exclusively to their assigned estate or regional cluster.
* **Corporate Commercial Team:** Full visibility across all estates, pricing matrices, and buyer terms.
* **Auditors / Finance:** Access to raw invoice logs, bill numbers, and reconciliation adjustments.
* **SSO Integration:** SAML 2.0 / OAuth2 / Okta integration replacing static password verification.

---

## 5. Pillar 4: Deep Tea Plantation & Factory Supply Chain Expansion
*Correlate downstream packaging data with upstream plantation agriculture:*

### 5.1 Green Leaf Intake & Factory Outturn %
* Connect with upstream plantation weighment records to calculate:
  $$\text{Outturn \%} = \frac{\text{Made Tea Net Qty (kg)}}{\text{Green Leaf Plucked (kg)}} \times 100$$
* Highlight estates that maximize made tea conversion efficiency per hectare.

### 5.2 Buyer Concentration & Portfolio Exposure Risk
* Dynamic buyer profile matrix analyzing purchasing volume, preferred grades, and price consistency of top corporate tea blenders and international importers.

---

## 6. Architecture Audit: 100% Dynamic Design & Current Status

### ✅ Fully Dynamic Subsystems
1. **Dynamic Tenant Auto-Discovery:** Discovers any `client_*` directory under `data/` automatically on server startup.
2. **Dynamic Schema Profiling:** Analyzes CSV datasets via DuckDB/Pandas, categorizing columns into continuous measures, categorical dimensions, and date timestamps with zero hardcoded column schemas.
3. **Universal Slicers & Commercial Matrix:** Slicers and matrix dimensions dynamically adapt to each tenant's schema (e.g. `Region` & `Grade` for Alpha, `Category` & `Sales Channel` for Beta).
4. **Deterministic Math Layer:** OLAP slicing, grouping, rankings, and weighted metrics are computed mathematically without LLM arithmetic.
5. **Dynamic AI Analysis Plan Generation:** Schema column profiles are passed to Gemini 2.5 Flash to generate context-specific SQL/OLAP plans without fixed query templates.
6. **Multi-Worker Shared Cache:** Cache files and DuckDB spill storage persist in `data/cache/` to ensure consistency across multiple server workers.

### 🚀 Production Hardening Upgrades
1. **Database-Backed Identity (Phase 2):** Upgrade tenant registry (`clients_config.py`) to PostgreSQL/SQLite with bcrypt password hashing and JWT session tokens.
2. **Fine-Grained User Roles:** Support multi-user accounts under a single tenant (e.g. Manager vs Head Office Auditor).
3. **Enterprise AI Quotas:** Move from direct API keys to enterprise managed gateways (e.g., Google Cloud Vertex AI) with Redis prompt caching for cost optimization.
