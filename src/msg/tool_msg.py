TOOL_DESC_MSG = [
        {
            "type": "function",
            "function": {
                "name": "retrieve_corrective_rag",
                "description": "Search local documents related to APPLE INC financials statement in 2026 Q1.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_portfolio_data",
                "description": (
                    "Read the entire Google Sheet portfolio database "
                    "'YuAgent Current Portfolio'. "
                    "This is the authoritative portfolio database and must be loaded "
                    "before making portfolio recommendations or modifying holdings.\n\n"

                    "Google Sheet Columns (A:P)\n"
                    "A Ticker\n"
                    "B Quantity\n"
                    "C Avg Price\n"
                    "D Current Price\n"
                    "E Sector\n"
                    "F Target Weight\n"
                    "G Current Weight\n"
                    "H Thesis\n"
                    "I Thesis Status\n"
                    "J Risk Limit\n"
                    "K Expected CAGR\n"
                    "L Confidence Score\n"
                    "M Entry Date\n"
                    "N Last Review Date\n"
                    "O Next Review Date\n"
                    "P Notes"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "append_portfolio_row",
                "description": (
                    "Append a NEW investment position to the bottom of the portfolio "
                    "Google Sheet.\n\n"

                    "Use ONLY when creating a brand-new holding.\n"

                    "Each parameter maps directly to one Google Sheet column.\n"

                    "Columns D (Current Price) and G (Current Weight) are normally "
                    "maintained externally and can be omitted."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker":{"type":"string"},
                        "quantity":{"type":"string"},
                        "avg_price":{"type":"string"},
                        "current_price":{"type":"string"},
                        "sector":{"type":"string"},
                        "target_weight":{"type":"string"},
                        "current_weight":{"type":"string"},
                        "thesis":{"type":"string"},
                        "thesis_status":{"type":"string"},
                        "risk_limit":{"type":"string"},
                        "expected_cagr":{"type":"string"},
                        "confidence_score":{"type":"string"},
                        "entry_date":{"type":"string"},
                        "last_review_date":{"type":"string"},
                        "next_review_date":{"type":"string"},
                        "notes":{"type":"string"}
                    }
                }
            }
        },
        {
            "type":"function",
            "function":{
                "name":"update_portfolio_row",
                "description":(
                    "Update selected fields of an EXISTING portfolio row.\n\n"

                    "Requires Google Sheet row_number.\n"

                    "Only fields supplied are updated.\n"

                    "Fields omitted remain unchanged.\n"

                    "Use this tool whenever modifying an existing holding "
                    "(quantity, thesis, review dates, confidence score, etc.)."
                ),
                "parameters":{
                    "type":"object",
                    "properties":{
                        "row_number":{"type":"integer"},
                        "ticker":{"type":"string"},
                        "quantity":{"type":"string"},
                        "avg_price":{"type":"string"},
                        "current_price":{"type":"string"},
                        "sector":{"type":"string"},
                        "target_weight":{"type":"string"},
                        "current_weight":{"type":"string"},
                        "thesis":{"type":"string"},
                        "thesis_status":{"type":"string"},
                        "risk_limit":{"type":"string"},
                        "expected_cagr":{"type":"string"},
                        "confidence_score":{"type":"string"},
                        "entry_date":{"type":"string"},
                        "last_review_date":{"type":"string"},
                        "next_review_date":{"type":"string"},
                        "notes":{"type":"string"}
                    },
                    "required":["row_number"]
                }
            }
        },
        {
            "type":"function",
            "function":{
                "name":"delete_portfolio_row",
                "description":(
                    "Delete an existing investment row from the portfolio Google Sheet.\n\n"

                    "Requires Google Sheet row_number.\n"

                    "Use ONLY after explicit user confirmation that the position should "
                    "be removed permanently."
                ),
                "parameters":{
                    "type":"object",
                    "properties":{
                        "row_number":{
                            "type":"integer"
                        }
                    },
                    "required":["row_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_brave_fresh_news",
                "description": "Search the web using Brave for the absolute latest news (last 24 hours) for specific tickers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query (e.g. 'MSFT news last 24h')"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_statements",
                "description": "Get historical financials from Yahoo Finance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker_symbol": {"type": "string", "description": "The stock ticker symbol (e.g., AAPL, TSLA)."}
                    },
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_ticker_news",
                "description": "Get recent news and articles for a stock ticker to analyze qualitative news sentiment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker_symbol": {"type": "string", "description": "The stock ticker symbol."}
                    },
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Run Python code to calculate financial ratios (Margins, ROE, CAGR, Debt/EBITDA) and build forecasts. Print outputs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The python code to execute. Standard output is captured and returned."}
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Perform a live web search to find current news, management guidance, and industry trends that are not in the local database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to look up on the web."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_financials_to_pdf",
                "description": "Generate a professionally styled PDF report with final explanations and tables. Use this when findings (such as forecasts or ratios) are generated and the user wants to export a PDF report that involves financial tables.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "The stock ticker symbol (e.g. AAPL)."},
                        "title": {"type": "string", "description": "Professional report title (e.g. AAPL Revenue Forecast & Valuation Analysis)."},
                        "explanation": {"type": "string", "description": "Executive summary and analysis paragraphs explaining the findings in details."},
                        "tables_data": {
                            "type": "object",
                            "description": "A dictionary where keys are table names (strings) and values are lists of lists representing rows and cells. Example: {'CAGR & Revenue Forecast': [['Metric', '2024', '2025'], ['Revenue ($B)', '394.33', '412.50'], ['Growth Rate', 'N/A', '4.6%']]}"
                        },
                        "output_filename": {"type": "string", "description": "Optional custom filename. Defaults to '<ticker>_financial_analysis_report.pdf'."}
                    },
                    "required": ["ticker", "title", "explanation", "tables_data"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_news_report_to_pdf",
                "description": "Generate a PDF report for news articles, qualitative sentiment, or profiles of people. Use this when the user wants to export non-financial news summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "The person or company name."},
                        "title": {"type": "string", "description": "Title of the news brief."},
                        "analysis_summary": {"type": "string", "description": "A narrative summary of the news findings."},
                        "news_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "source": {"type": "string"},
                                    "date": {"type": "string"},
                                    "summary": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["subject", "title", "analysis_summary", "news_items"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_telegram_message",
                "description": "Send a formatted message to the user's Telegram bot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to send."
                        }
                    },
                    "required": ["message"]
                }
            }
        }
    ]
