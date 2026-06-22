import yfinance as yf
from langsmith import traceable

def format_df(df) -> str:
    try:
        return df.to_markdown()
    except Exception:
        try:
            return df.to_string()
        except Exception as e:
            return f"Formatting error: {str(e)}"

@traceable(name="Tool: Get Financial Statements")
def get_financial_statements(ticker_symbol: str) -> str:
    """Retrieves historical financials (Income Statement, Balance Sheet, Cash Flow) for the requested ticker.
    
    Args:
        ticker_symbol: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
        
    Returns:
        A formatted string containing the financial statements as markdown or text tables.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch statements
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        output = []
        output.append(f"### Historical Financial Data for {ticker_symbol.upper()} ###\n")
        
        if financials is not None and not financials.empty:
            output.append("--- INCOME STATEMENT ---")
            output.append(format_df(financials.head(15)))
            output.append("")
        else:
            output.append("Income Statement data is unavailable.")
            
        if balance_sheet is not None and not balance_sheet.empty:
            output.append("--- BALANCE SHEET ---")
            output.append(format_df(balance_sheet.head(15)))
            output.append("")
        else:
            output.append("Balance Sheet data is unavailable.")
            
        if cashflow is not None and not cashflow.empty:
            output.append("--- CASH FLOW STATEMENT ---")
            output.append(format_df(cashflow.head(15)))
            output.append("")
        else:
            output.append("Cash Flow statement data is unavailable.")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error retrieving financial statements for ticker {ticker_symbol}: {str(e)}"

@traceable(name="Tool: Get Ticker News")
def get_ticker_news(ticker_symbol: str) -> str:
    """Retrieves recent news articles and sentiment details for the requested ticker.
    
    Args:
        ticker_symbol: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
        
    Returns:
        A formatted string of recent news headlines, publishers, and links.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        news_list = ticker.news
        
        if not news_list:
            return f"No news articles found for ticker {ticker_symbol}."
            
        output = []
        output.append(f"### Recent News for {ticker_symbol.upper()} ###\n")
        
        for item in news_list[:8]:  # Limit to top 8 news items
            title = item.get("title", "No Title")
            publisher = item.get("publisher", "Unknown Publisher")
            link = item.get("link", "")
            provider_publish_time = item.get("providerPublishTime", 0)
            
            output.append(f"- **{title}**")
            output.append(f"  Publisher: {publisher}")
            if link:
                output.append(f"  Link: {link}")
            output.append("")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error retrieving news for ticker {ticker_symbol}: {str(e)}"
