# Dynamic Portfolio Optimization

Monthly rebalanced portfolio using a Variational LSTM for return and volatility forecasts, with a return–drawdown optimizer for allocation. Here is the workflow overview:

<p align="center">
  <img src="pic/workflow.png" width="60%" alt="workflow">
</p>

### Stage 1: Return and Volatility Prediction (Variational LSTM)

Learn a distribution of future returns $p(return | sequence)$ using a Variational LSTM.

- **Given:** Historical sequences of features (price, volume, technical indicators) for each asset over $\texttt{LOOKBACK} = 66$ days
- **Predict:** Mean return $\hat{\mu}$ and variance $\hat{\sigma}^2$ over $\texttt{FORECAST HORIZON} = 21$ days
- **Method:** Variational LSTM minimizing a time-weighted loss:

$$\mathcal{L} = \underbrace{\frac{1}{N}\sum_i w_i \cdot \text{NLL}_i}_{\text{time-weighted prediction}} + \underbrace{\beta \cdot \text{KL}(q(z|x) \| p(z))}_{\text{latent regularization}} + \underbrace{0.5 \cdot \text{direction penalty}}_{\text{sign mismatch}}$$

Where:
- **NLL** (Gaussian negative log-likelihood): rewards accurate predictions with appropriate uncertainty
- **KL divergence**: regularizes latent space to stay close to prior N(0,I)
- **Direction loss**: penalizes sign mismatches between predicted and actual returns

### Stage 2: Portfolio Allocation (Return-Drawdown Optimizer)

Optimize portfolio weights $w \in \mathbb{R}^n$ to maximize return/drawdown(proxy) ratio.

- **Given:** Predicted returns $\hat{\mu}$ and volatilities $\hat{\sigma}$ from Stage 1
- **Find:** Weights $w$ that solve:

$$\min_w \; -\text{ratio}(w)$$

$$\text{subject to} \quad \sum_{j=1}^{n} w_j = 1, \quad 0 \leq w_j \leq 1$$

Where:

$$\text{ratio} = \begin{cases}
\frac{\mu_p}{\text{MDD}} + \alpha \mu_p & \text{if } \mu_p > 0 \\
\mu_p \cdot \sqrt{\texttt{FORECAST HORIZON}} \cdot \text{MDD} & \text{if } \mu_p \leq 0
\end{cases}$$

- **Portfolio return:** $\mu_p = w^T \hat{\mu}$; this is the weighted sum of predicted returns for each asset
- **Portfolio volatility:** $\sigma_p = \sqrt{w^T \hat{H} w}$
- **Max-drawdown proxy:** $\text{MDD} = \max(10^{-4}, 2\sqrt{\texttt{FORECAST HORIZON}}\cdot\sigma_p)$; $10^{-4}$ is a small constant to handle the case when $\sigma_p \approx 0$
- **Covariance:** $\hat{H} = D\cdot\Sigma_{\text{corr}}\cdot D$ where $D = \text{diag}(\hat{\sigma}_1, \ldots, \hat{\sigma}_n)$
- **Method:** SLSQP optimizer (long-only, fully invested)

### Stage 3: Backtest (Monthly Rebalance)

Monthly rebalance backtest applies optimized weights (from Stage 2) to actual returns and compounds capital. Performance measured via Sharpe ratio and cumulative returns. 

For the Sharpe ratio, we use the following formula:
$$S = \alpha \cdot \frac{\mathbb{E}[R_p - R_f]}{\sigma_p} = \sqrt{252} \cdot \frac{\bar{R}_p - R_f}{\sigma_p}$$

where:
- $R_p$: portfolio return
- $R_f$: risk-free rate
- $\sigma_p$: standard deviation of portfolio (excess) returns
- $\alpha = \sqrt{252}$: annualization factor
