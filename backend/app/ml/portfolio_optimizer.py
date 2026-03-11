"""
Portfolio weight optimizer using Return/MaxDD + alpha * Return objective.
Ported from Previous/Project/src/optimization/solver.py -- CPU-only (no GPU helpers).
"""
import numpy as np
from scipy.optimize import minimize


class PortfolioOptimizer:
    def __init__(self, risk_free_rate: float = 0.0, alpha: float = 0.2):
        self.risk_free_rate = risk_free_rate
        self.alpha = alpha

    def optimize(
        self,
        expected_returns: np.ndarray,
        sigma_hat: np.ndarray,
        historical_returns: np.ndarray | None = None,
    ) -> np.ndarray:
        n_assets = len(expected_returns)
        initial_weights = np.ones(n_assets) / n_assets
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))

        result = minimize(
            self._objective,
            initial_weights,
            args=(expected_returns, sigma_hat, historical_returns),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        if not result.success:
            return initial_weights
        return result.x

    def _objective(
        self,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        sigma_hat: np.ndarray,
        historical_returns: np.ndarray | None,
    ) -> float:
        port_return = float(np.sum(weights * expected_returns))
        port_vol = float(np.sqrt(weights.T @ sigma_hat @ weights))
        max_dd = max(1e-4, 2.0 * port_vol)

        if port_return >= 0:
            ratio = (port_return / max_dd) + self.alpha * port_return
        else:
            ratio = port_return * max_dd

        return -ratio

    @staticmethod
    def construct_covariance(predicted_vols: np.ndarray, historical_correlation: np.ndarray) -> np.ndarray:
        D = np.diag(predicted_vols)
        return D @ historical_correlation @ D
