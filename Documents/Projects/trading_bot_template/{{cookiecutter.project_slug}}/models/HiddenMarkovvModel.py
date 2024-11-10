from hmmlearn.hmm import GaussianHMM
import numpy as np

# Prepare features (log returns and volatility)
def prepare_features(data):
    log_returns = np.log(data['Close'] / data['Close'].shift(1))
    volatility = log_returns.rolling(window=10).std()
    features = np.column_stack([log_returns, volatility])
    return features[~np.isnan(features).any(axis=1)]  # Remove NaNs

# Train HMM model
def train_hmm(features, n_states=3):
    hmm_model = GaussianHMM(n_components=n_states, covariance_type="full")
    hmm_model.fit(features)
    return hmm_model

# Predict market regime
def predict_regime(hmm_model, features):
    hidden_states = hmm_model.predict(features)
    return hidden_states[-1]  # Last detected state
