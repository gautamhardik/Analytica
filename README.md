# Analytica — E-Commerce Analytics & ML Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000.svg?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Polars](https://img.shields.io/badge/Polars-1.0-CDC8B0.svg?logo=polars&logoColor=black)](https://pola.rs)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0-FF6F00.svg?logo=lightgbm&logoColor=white)](https://lightgbm.readthedocs.io)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com)
[![CI](https://github.com/gautamhardik/Analytica/actions/workflows/ci.yml/badge.svg)](https://github.com/gautamhardik/Analytica/actions/workflows/ci.yml)

A full-stack analytics platform built on the Olist Brazilian e-commerce dataset (100K+ orders). It covers the whole pipeline a data team actually owns: a dimensional warehouse, an async API layer with measured caching gains, two applied ML models, and a dashboard that turns all of it into something a non-technical stakeholder can read.

Built to demonstrate one thing: I can take a raw dataset to a working, benchmarked, production-inspired system — not just a notebook.

---


## Demo

https://github.com/user-attachments/assets/e9e9354d-bc9d-4434-b829-712ba0c8069a

---



## Project motivation

Modern retail businesses generate transactional data from multiple sources, but business users need decisions, not tables. Analytica demonstrates an end-to-end analytics workflow — from ingestion and warehousing to machine learning and executive dashboards — in a production-inspired architecture.

---

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | Next.js · React · TypeScript · TanStack Query |
| Backend | FastAPI · SQLAlchemy · Redis |
| Data | MySQL · Polars |
| Machine Learning | LightGBM · Scikit-learn |
| Deployment | Docker |

---

## What this project demonstrates

| Area | What I built | Why it matters |
|---|---|---|
| Data modeling | Star schema (1 fact table, 4 dimensions) in MySQL, loaded via a Polars ETL pipeline | Shows I can design for query performance, not just get data into a table |
| Backend engineering | Async FastAPI service with Redis-backed caching and tuned connection pooling | Shows I understand where latency actually comes from in a real API |
| Applied ML | LightGBM revenue forecasting + RFM/K-Means customer segmentation, both validated with standard metrics | Shows I can go from EDA to a model with a defensible evaluation, not just `.fit()` |
| Product sense | A 10-page Next.js dashboard translating the above into an executive-readable tool | Shows I can close the loop from analysis to a decision-maker-facing product |

---

## Architecture

```mermaid
flowchart TD
    subgraph Data Layer
        A[Olist Raw CSVs] -->|Polars ETL| B[(MySQL Star Schema)]
        B --> C[reporting_sales_summary]
        B --> D[reporting_customer_summary]
        B --> E[reporting_state_summary]
    end

    subgraph ML Layer
        F[LightGBM Forecast Model] --> H[FastAPI Backend]
        G[RFM K-Means Segmentation] --> H
        B -->|async SQLAlchemy| H
    end

    subgraph API Layer
        H[FastAPI Async Backend] <--> I[Redis / TTL Cache]
    end

    subgraph Presentation Layer
        J[Next.js Dashboard] <-->|TanStack Query| H
        J --> K[AI Executive Summary]
        J --> L[Filter Bar]
    end
```

---

## Engineering decisions (and why I made them)

**Why a star schema over a snowflake schema:** the dashboard's query patterns are almost entirely single-join aggregations (revenue by state, revenue by month, revenue by segment). A star schema keeps those joins shallow and avoids the multi-hop joins a snowflake design would force for the same queries.

**Why Polars over pandas for ETL:** the transform step involves several full-table joins and groupbys across ~100K+ rows repeatedly during development iteration. Polars' columnar, multi-threaded execution made iteration noticeably faster than pandas on the same transforms — useful during development, not just a benchmark flex.

**Why LightGBM over ARIMA/Prophet for forecasting:** the revenue series has irregular seasonality and several categorical drivers (state, category) that a pure time-series model can't easily incorporate. A gradient-boosted tree model lets me treat forecasting as regression with time-based and categorical features, at the cost of losing some classical time-series interpretability — a tradeoff I'm explicit about in the model docs.

**Why K-Means over hierarchical/DBSCAN for segmentation:** RFM features are low-dimensional and roughly convex per cluster after scaling, which is exactly where K-Means performs well and stays interpretable for a business audience. I validated cluster count with silhouette score and Davies-Bouldin index rather than picking K arbitrarily.

**Why a caching layer at all:** several endpoints aggregate across the full fact table on every request. Rather than optimize every query indefinitely, I cached the aggregation layer — the more common and more defensible fix in a real system with a mixed read/write pattern.

---

## Performance

Measured with live HTTP request probes on a local dev environment (single machine, not load-tested under concurrency — see note below).

| Endpoint | Cold | Cached | Change |
|---|---|---|---|
| `/api/v1/executive` | 277.6 ms | 1.2 ms | −99.5% |
| `/api/v1/customers` | 1044.6 ms | 1.2 ms | −99.8% |
| `/api/v1/segmentation/overview` | 111.7 ms | 3.9 ms | −96.5% |
| `/api/v1/sales` | 11.7 ms | 1.8 ms | −84.6% |
| `/api/v1/geography` | 7.1 ms | 1.2 ms | −83.0% |
| `/api/v1/products` | 7.0 ms | 1.4 ms | −80.0% |
| `/api/v1/ai/executive-summary` | 3.4 ms | 1.2 ms | −64.7% |
| `/api/v1/forecasting/overview` | 2.4 ms | 1.7 ms | −29.1% |

**Note on methodology:** "cold" is the first request after cache expiry (full DB aggregation); "cached" is a subsequent request served from the TTL/Redis layer. These are single-request timings on local hardware, not averaged over load — the multi-second `/customers` cold time in particular reflects an unindexed aggregation path I identified but haven't fully optimized independent of caching. I'm listing that honestly rather than only showing the flattering number.

---

## Repository structure

```text
Analytica/
├── backend/            # FastAPI app — core, domains, services, repositories, routers
├── frontend/            # Next.js 16 dashboard — App Router, TanStack Query
├── ETL/                 # extract.py / transform.py / load.py (Polars → MySQL)
├── SQL/                 # schema, indexes, reporting/materialized views
├── DOCS/                 # data dictionary, dimensional model, source-to-warehouse mapping
├── Customer_Segmentation/  # RFM + K-Means pipeline
├── Revenue Forecasting/    # LightGBM pipeline
└── NOTEBOOKS/            # EDA and model development
```

---

## Setup

### Docker (recommended)

```bash
docker compose up -d
```
Dashboard: `http://localhost:3000` · API docs: `http://localhost:8000/docs`
Run ETL: `docker compose --profile etl run --rm etl`

### Manual

```bash
# Database
mysql -u root -p < SQL/create_database.sql
mysql -u root -p brazilian_ecommerce_dw < SQL/dump_brazilian_ecommerce_dw.sql

# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# create .env with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, CORS_ORIGINS
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd frontend && npm install && npm run dev
```

Requires Python 3.10+, Node 18+, MySQL 8.0+, Redis 7+ (optional — falls back to in-process TTL cache).

---

## Testing

```bash
cd backend && python -m pytest tests/
cd frontend && npm run test
```

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check + DB connection status |
| GET | `/api/v1/executive` | Executive dashboard payload |
| GET | `/api/v1/sales` | Revenue trends, MoM growth |
| GET | `/api/v1/customers` | Customer health, repeat rate, spending tiers |
| GET | `/api/v1/products` | Category and seller performance |
| GET | `/api/v1/geography` | State-level revenue and freight metrics |
| GET | `/api/v1/segmentation/overview` | RFM/K-Means personas + PCA coordinates |
| GET | `/api/v1/forecasting/overview` | LightGBM forecast + residuals |
| GET | `/api/v1/ai/executive-summary` | Automated executive summary synthesis |

---

## What I'd build next

- Load testing (Locust/k6) on the cached endpoints to validate the latency numbers hold under concurrency, not just single-request probes.
- An index on the customer aggregation path to fix the 1s cold-query time at the source, rather than relying entirely on caching to mask it.
- Backtesting the LightGBM forecast against a rolling window rather than a single holdout split.

---

## Dataset & license

- Data: [Olist Brazilian E-Commerce Dataset (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- License: MIT
