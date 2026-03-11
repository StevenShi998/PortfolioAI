"""
ML hyperparameters and ticker universe.
Sourced from Previous/Project/src/config.py and the notebook.
"""

LOOKBACK = 66
FORECAST_HORIZON = 21

BATCH_SIZE = 1024
EPOCHS = 50
LEARNING_RATE = 0.001
HIDDEN_DIM = 128
LATENT_DIM = 32

ALPHA = 0.72

# Strength of indicator-preference tilt on predicted returns (0 = no tilt).
TILT_STRENGTH = 0.15

# Recommendation cap and risk-based diversification.
MAX_RECOMMENDED_STOCKS = 8
RISK_TO_MAX_STOCKS = {"conservative": 8, "moderate": 6, "aggressive": 4}

START_DATE = "2022-01-01"
END_DATE = "2026-03-01"

# At least 10 tickers per S&P 500 (GICS) sector; SPY/QQQ at end for benchmark/universe.
ALL_TICKERS = [
    # Energy (10+)
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "DVN", "PBR", "LEU", "OKLO",
    # Materials (10+)
    "LIN", "APD", "SHW", "ECL", "FCX", "NUE", "NEM", "VMC", "PPG", "DOW", "ALB", "EMN", "DD",
    # Industrials (10+)
    "CAT", "HON", "UPS", "UNP", "RTX", "LMT", "GE", "DE", "BA", "GD", "WM", "RSG", "CARR", "EMR",
    # Consumer Discretionary (10+)
    "AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "LOW", "TJX", "BKNG", "ORLY", "GM", "F", "DHI", "LEN",
    # Consumer Staples (10+)
    "PG", "KO", "WMT", "COST", "PEP", "PM", "MDLZ", "CL", "KMB", "FDP", "GIS", "SJM", "STZ", "KHC",
    # Health Care (10+)
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY", "AMGN", "GILD", "CVS", "ELV",
    # Financials (10+)
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SCHW", "USB", "PNC", "COF", "TFC", "HOOD",
    # Information Technology (10+)
    "AAPL", "MSFT", "NVDA", "ORCL", "AVGO", "ADBE", "CRM", "CSCO", "AMD", "INTC", "IBM", "QCOM", "NOW", "INTU",
    # Communication Services (10+)
    "GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA", "TTWO", "WBD", "SPOT", "FOXA",
    # Utilities (10+)
    "NEE", "DUK", "SO", "D", "AEP", "XEL", "SRE", "EXC", "WEC", "ED", "ETR", "AEE", "ES", "AWK",
    # Real Estate (10+)
    "PLD", "AMT", "EQIX", "O", "PSA", "SPG", "WELL", "VTR", "EQR", "INVH", "MAA", "UDR", "ARE", "DLR",
    # ETFs / benchmark
    "QQQ", "SPY",
]

FEATURE_NAMES = ["log_ret", "volatility", "trend_20", "trend_50", "beta", "log_vol", "smi"]
