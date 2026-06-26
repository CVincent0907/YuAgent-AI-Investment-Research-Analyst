# Financial Analyst Agent Architecture

## High-Level Architecture

```text
                          ┌──────────────────────────┐
                          │        User Query        │
                          └────────────┬─────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────┐
                    │ Long-Term Memory Retrieval (LTM) │
                    │ Retrieve relevant past context   │
                    └────────────┬─────────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────────────┐
                    │ Build System Prompt              │
                    │ - Agent Role                     │
                    │ - Conversation History           │
                    │ - Long-Term Memory               │
                    └────────────┬─────────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────────────┐
                  │ Agnes AI (Reasoning Engine / Planner) │
                  └─────────────────┬─────────────────────┘
                                    │
                                    ▼
                  ┌───────────────────────────────────────┐
                  │         ReAct Agent Loop              │
                  │      (Maximum 15 Iterations)          │
                  └─────────────────┬─────────────────────┘
                                    │
                     ┌──────────────┼───────────────┐
                     │              │               │
                     ▼              ▼               ▼
             Think / Plan     Call Tool      Observe Result
                     │              │               │
                     └──────────────┴───────────────┘
                                    │
                     Continue reasoning if needed
                                    │
                     Stop when answer is complete
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │ Candidate Final Answer           │
                    └────────────┬─────────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────────────┐
                    │ Gatekeeper LLM                   │
                    │ YES / NO Validation              │
                    └────────────┬─────────────────────┘
                                 │
                     YES         │          NO
                      │          │
                      ▼          ▼
             Save to Long-Term Memory
                      │
                      ▼
               Return Final Answer
```

---

# Internal Corrective RAG Architecture

The `retrieve_corrective_rag` tool itself contains another agentic workflow built with LangGraph.

```text
                 Query
                   │
                   ▼
      Hybrid Retrieval (Dense + BM25)
                   │
                   ▼
        FlashRank Cross Encoder
               Reranking
                   │
                   ▼
        Evaluate Context Quality
         (LLM + Similarity Score)
                   │
         ┌─────────┴─────────┐
         │                   │
     Sufficient          Insufficient
         │                   │
         ▼                   ▼
      Return           Web Search
                             │
                             ▼
                  Merge Local + Web Results
                             │
                             ▼
                      FlashRank Again
                             │
                             ▼
                    Final Retrieved Context
```

---

# ReAct Tool Invocation Flow

During each reasoning iteration Agnes may decide to invoke **zero, one, or multiple tools**.

```
Iteration 1
------------
Think
↓
Call retrieve_corrective_rag
↓
Observe retrieved context

Iteration 2
------------
Think
↓
Call get_financial_statements
↓
Observe financial data

Iteration 3
------------
Think
↓
Call execute_python_code
↓
Observe calculated ratios

Iteration 4
------------
Think
↓
Call search_brave_fresh_news
↓
Observe market news

Iteration 5
------------
Think
↓
Generate final investment thesis

Stop
```

The loop continues until:

- no more tool calls are requested,
- the answer is complete, or
- **15 iterations** have been reached.

---

# Available Tools

## Knowledge Retrieval

| Tool | Purpose |
|-------|---------|
| retrieve_corrective_rag | Hybrid RAG retrieval (Vector + BM25 + FlashRank + Corrective Web Search) |
| search_web | DuckDuckGo search |
| search_brave_fresh_news | Brave Search API for recent news |

---

## Financial Data

| Tool | Purpose |
|-------|---------|
| get_financial_statements | Yahoo Finance financial statements |
| get_ticker_news | Yahoo Finance news |

---

## Portfolio Management (Google Sheets MCP)

| Tool | Purpose |
|-------|---------|
| get_portfolio_data | Read portfolio |
| append_portfolio_row | Add holding |
| update_portfolio_row | Modify holding |
| delete_portfolio_row | Remove holding |

---

## Analysis

| Tool | Purpose |
|-------|---------|
| execute_python_code | Financial modelling, valuation, forecasting, ratios |

---

## Reporting

| Tool | Purpose |
|-------|---------|
| export_financials_to_pdf | Export financial report |
| export_news_report_to_pdf | Export news report |

---

# Corrective RAG Components

This RAG implementation is significantly more advanced than traditional RAG.

```
User Query
     │
     ▼
Dense Vector Search
     │
     ├─────────────┐
     ▼             ▼
BM25 Search   Semantic Search
     │             │
     └──────┬──────┘
            ▼
 Merge Candidate Documents
            │
            ▼
 FlashRank Cross Encoder
            │
            ▼
 Top Ranked Context
            │
            ▼
 Context Evaluation
            │
      ┌─────┴──────┐
      │            │
      ▼            ▼
 Enough?        Not Enough
      │            │
      ▼            ▼
 Return      Search Web
                   │
                   ▼
          Merge Everything
                   │
                   ▼
        FlashRank Again
                   │
                   ▼
          Final Context
```

---

# Strengths of This Architecture

## 1. Hybrid Retrieval

Combines:

- Dense embeddings
- Sparse BM25
- FlashRank reranking

instead of relying on vector search alone.

---

## 2. Corrective RAG

Instead of immediately falling back to the web, the system first evaluates whether the retrieved local context is sufficient.

---

## 3. ReAct Agent

The LLM is not limited to one retrieval step.

It can:

- think,
- call tools,
- inspect results,
- decide the next action,

for up to **15 reasoning iterations**.

---

## 4. Tool-Oriented Reasoning

The agent can autonomously combine:

- Local RAG
- Financial APIs
- Market News
- Python computation
- Google Sheets portfolio management
- PDF generation

within a single reasoning session.

---

## 5. Persistent Memory

The system incorporates both:

- Short-term conversational memory
- Long-term memory retrieval

allowing follow-up questions to build on previous interactions.

---

# Best Use Cases

This architecture performs particularly well for:

- Equity research
- Fundamental stock analysis
- Investment thesis generation
- Financial statement analysis
- Earnings report interpretation
- Portfolio management
- Market news synthesis
- Valuation modelling
- Multi-step financial reasoning
- Long-running research conversations
- Financial report generation
- Decision support for investment professionals

Unlike a standard chatbot, the system behaves as a **financial research agent**, capable of planning, gathering evidence from multiple sources, performing calculations, and synthesizing the results into a coherent investment analysis.



# Demo Use Cases

## 1. Long-Term Equity Research

**Prompt**

```text
Analyze Apple (AAPL) as a long-term investment and provide a Buy, Hold, or Sell recommendation with supporting evidence.
```

---

## 2. Fundamental Analysis

**Prompt**

```text
Perform a complete fundamental analysis of Microsoft and explain its financial strengths, weaknesses, opportunities, and risks.
```

---

## 3. Financial Statement Analysis

**Prompt**

```text
Analyze Tesla's financial statements over the past three years and identify the major trends in revenue, profitability, cash flow, and debt.
```

---

## 4. Earnings Report Analysis

**Prompt**

```text
Summarize Nvidia's latest earnings report and explain whether the company exceeded market expectations.
```

---

## 5. Company Valuation

**Prompt**

```text
Estimate Amazon's intrinsic value using a discounted cash flow (DCF) model and explain your assumptions.
```

---

## 6. Financial Ratio Analysis

**Prompt**

```text
Calculate Apple's Gross Margin, Operating Margin, Net Margin, ROE, ROA, Debt-to-Equity Ratio, and Current Ratio, then explain what each metric indicates about the company's financial health.
```

---

## 7. Revenue Forecasting

**Prompt**

```text
Forecast Microsoft's revenue for the next three years based on historical financial performance and recent management guidance.
```

---

## 8. Industry Research

**Prompt**

```text
Research the AI semiconductor industry and summarize the major growth drivers, risks, competitive landscape, and long-term outlook.
```

---

## 9. Market News Analysis

**Prompt**

```text
Summarize the latest news surrounding AMD and explain how these developments could impact the company's future financial performance.
```

---

## 10. Investment Comparison

**Prompt**

```text
Compare Apple, Microsoft, Nvidia, Amazon, and Alphabet as long-term investments and rank them from strongest to weakest with detailed reasoning.
```

---

## 11. Portfolio Review

**Prompt**

```text
Review my investment portfolio and identify its strengths, weaknesses, concentration risks, diversification opportunities, and overall risk profile.
```

---

## 12. Add a New Portfolio Position

**Prompt**

```text
Add Microsoft (MSFT) to my portfolio with:

- Quantity: 20
- Average Price: 438.25
- Sector: Technology
- Expected CAGR: 15%
- Confidence Score: 9
- Investment Thesis: Leader in enterprise AI and cloud computing.
```

---

## 13. Update an Existing Position

**Prompt**

```text
Update my Apple portfolio position.

Expected CAGR: 18%
Confidence Score: 8
Risk Limit: Medium
Notes: Increase allocation following strong AI-related earnings guidance.
```

---

## 14. Remove a Portfolio Position

**Prompt**

```text
Remove Intel (INTC) from my investment portfolio.
```

---

## 15. Investment Thesis Generation

**Prompt**

```text
Generate a comprehensive investment thesis for Nvidia covering business overview, competitive advantages, financial performance, valuation, growth opportunities, risks, and conclude with a Buy, Hold, or Sell recommendation.
```

---

## 16. Generate Financial Report

**Prompt**

```text
Generate a professional PDF report containing a complete financial analysis of Apple.
```

---

## 17. Generate News Report

**Prompt**

```text
Generate a PDF summarizing the latest news related to Tesla and explain the potential impact on investors.
```

---

## 18. Image-Based Financial Analysis

**Prompt**

```text
Analyze this uploaded earnings presentation slide, summarize the important financial information, and explain its impact on the company's future outlook.
```

---

## 19. Stock Screening

**Prompt**

```text
Identify five technology companies with strong financial fundamentals, sustainable competitive advantages, attractive long-term growth prospects, and reasonable valuations.
```

---

## 20. Complete Investment Research Report

**Prompt**

```text
I am considering investing in Amazon.

Produce a comprehensive investment research report that includes:

- Business Overview
- Historical Financial Performance
- Revenue and Earnings Growth
- Profitability Analysis
- Cash Flow Analysis
- Balance Sheet Strength
- Valuation
- Management Guidance
- Industry Outlook
- Competitive Landscape
- Recent News
- Key Risks
- Three-Year Outlook
- Final Buy, Hold, or Sell Recommendation
```
