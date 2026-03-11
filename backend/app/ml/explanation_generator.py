"""
Translates raw model outputs into plain-English explanations for each stock.
This is the bridge between the ML engine and the user-facing UI.
"""
import numpy as np
import pandas as pd


def generate_explanations(
    assets: list[str],
    weights: dict[str, float],
    feature_df: pd.DataFrame,
    pred_returns: np.ndarray,
    pred_vols: np.ndarray,
) -> list[dict]:
    """
    Produce a list of explanation dicts, one per asset with weight > 0.1%.
    Each dict: {ticker, allocation_pct, reasoning_text, metrics}.
    """
    explanations: list[dict] = []
    latest = feature_df.iloc[-1]

    for i, asset in enumerate(assets):
        alloc = weights.get(asset, 0.0)
        if alloc < 0.001:
            continue

        metrics = _extract_metrics(asset, latest, pred_returns[i], pred_vols[i])
        reasoning = _build_reasoning(asset, metrics)

        explanations.append(
            {
                "ticker": asset,
                "allocation_pct": round(alloc * 100, 2),
                "reasoning_text": reasoning,
                "metrics": metrics,
            }
        )

    explanations.sort(key=lambda x: x["allocation_pct"], reverse=True)
    return explanations


def _extract_metrics(asset: str, latest_row: pd.Series, pred_return: float, pred_vol: float) -> dict:
    def _safe(col: str) -> float | None:
        key = f"{asset}_{col}"
        if key in latest_row.index:
            val = latest_row[key]
            if pd.notna(val):
                return round(float(val), 4)
        return None

    return {
        "predicted_return": round(float(pred_return), 4),
        "predicted_volatility": round(float(pred_vol), 4),
        "trend_20": _safe("trend_20"),
        "trend_50": _safe("trend_50"),
        "beta": _safe("beta"),
        "smi": _safe("smi"),
        "volatility": _safe("volatility"),
    }


def _build_reasoning(asset: str, m: dict) -> str:
    parts: list[str] = []

    pred_ret = m.get("predicted_return", 0)
    if pred_ret > 0.03:
        parts.append("The model expects a strong positive return over the next month.")
    elif pred_ret > 0:
        parts.append("The model expects a modest positive return over the next month.")
    else:
        parts.append("Included for diversification despite a muted return forecast.")

    trend20 = m.get("trend_20")
    if trend20 is not None:
        if trend20 > 0.02:
            parts.append("Currently trading above its 20-day moving average, signaling short-term upward momentum.")
        elif trend20 < -0.02:
            parts.append("Trading below its 20-day moving average, which may present a value opportunity.")

    trend50 = m.get("trend_50")
    if trend50 is not None:
        if trend50 > 0.05:
            parts.append("Strong medium-term uptrend relative to the 50-day average.")
        elif trend50 < -0.05:
            parts.append("Medium-term trend is currently negative relative to the 50-day average.")

    smi = m.get("smi")
    if smi is not None:
        if smi > 0.4:
            parts.append("Stochastic Momentum Index indicates overbought conditions; may see a pullback.")
        elif smi < -0.4:
            parts.append("SMI suggests oversold conditions, which can signal a reversal upward.")
        else:
            parts.append("Momentum indicators are in a neutral range.")

    vol = m.get("volatility")
    pred_vol = m.get("predicted_volatility", 0)
    if vol is not None and vol < 0.2:
        parts.append("Relatively low volatility, contributing to portfolio stability.")
    elif vol is not None and vol > 0.5:
        parts.append("Higher volatility stock; allocated conservatively to manage risk.")

    beta = m.get("beta")
    if beta is not None:
        if beta > 1.3:
            parts.append(f"Beta of {beta:.2f} means it amplifies market moves.")
        elif beta < 0.7:
            parts.append(f"Beta of {beta:.2f} provides a defensive profile.")

    return " ".join(parts)
