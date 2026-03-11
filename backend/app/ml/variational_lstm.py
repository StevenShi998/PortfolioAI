"""
Variational LSTM for return distribution prediction.
Ported from Previous/Project/src/models/variational_lstm.py.
"""
import tensorflow as tf
from tensorflow.keras import layers

from .config import HIDDEN_DIM, LATENT_DIM


class Sampling(layers.Layer):
    def call(self, inputs):
        z_mean, z_log_var = inputs
        batch = tf.shape(z_mean)[0]
        dim = tf.shape(z_mean)[1]
        epsilon = tf.random.normal(shape=(batch, dim))
        return z_mean + tf.exp(0.5 * z_log_var) * epsilon


class VariationalLSTM(tf.keras.Model):
    def __init__(self, input_dim: int, latent_dim: int = LATENT_DIM, hidden_dim: int = HIDDEN_DIM,
                 beta: float = 0.02, recency_weight: float = 2.0, **kwargs):
        super().__init__(**kwargs)
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.beta = beta
        self.recency_weight = recency_weight

        self.lstm = layers.LSTM(hidden_dim, return_sequences=False)
        self.z_mean_dense = layers.Dense(latent_dim, name="z_mean")
        self.z_log_var_dense = layers.Dense(latent_dim, name="z_log_var")
        self.sampling = Sampling()

        self.decoder_hidden = layers.Dense(hidden_dim, activation="relu")
        self.return_mean = layers.Dense(1, name="return_mean")
        self.return_log_var = layers.Dense(1, name="return_log_var")

        self.kl_loss_tracker = tf.keras.metrics.Mean(name="kl_loss")

    def call(self, inputs, training=False):
        h = self.lstm(inputs)
        z_mean = self.z_mean_dense(h)
        z_log_var = self.z_log_var_dense(h)
        # At inference use z_mean only for deterministic recommendations; sample during training.
        z = self.sampling([z_mean, z_log_var]) if training else z_mean

        d = self.decoder_hidden(z)
        pred_mean = self.return_mean(d)
        pred_log_var = self.return_log_var(d)

        kl_loss = -0.5 * tf.reduce_mean(1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var), axis=-1)
        self.kl_loss_tracker.update_state(kl_loss)
        return pred_mean, pred_log_var, kl_loss

    @property
    def metrics(self):
        return [self.kl_loss_tracker]

    def train_step(self, data):
        if isinstance(data, (list, tuple)) and len(data) == 3:
            x, y, sample_age = data
        elif isinstance(data, (list, tuple)) and len(data) == 2:
            x, y = data
            sample_age = tf.zeros(tf.shape(y)[0])
        else:
            x, y = data[0], data[1]
            sample_age = tf.zeros(tf.shape(y)[0])

        sample_age = tf.cast(sample_age, tf.float32)
        y = tf.cast(y, tf.float32)

        with tf.GradientTape() as tape:
            y_pred_mean, y_pred_log_var, kl_loss = self(x, training=True)
            y_pred_log_var = tf.clip_by_value(y_pred_log_var, -10.0, 10.0)

            loss_nll = 0.5 * y_pred_log_var + 0.5 * tf.square(y - y_pred_mean) / tf.exp(y_pred_log_var)

            loss_direction = -tf.tanh(y) * tf.tanh(y_pred_mean)
            loss_direction = tf.reduce_mean(tf.maximum(0.0, loss_direction))

            max_age = tf.maximum(tf.reduce_max(sample_age), 1e-6)
            time_weights = tf.exp(-self.recency_weight * sample_age / max_age)
            time_weights = tf.cast(time_weights, loss_nll.dtype)

            weighted_nll = loss_nll * tf.expand_dims(time_weights, axis=-1)
            total_loss = tf.reduce_mean(weighted_nll) + self.beta * tf.reduce_mean(kl_loss) + 0.5 * loss_direction

        grads = tape.gradient(total_loss, self.trainable_weights)
        self.optimizer.apply_gradients(zip(grads, self.trainable_weights))
        return {"loss": total_loss, "nll": tf.reduce_mean(loss_nll), "kl": self.kl_loss_tracker.result()}

    def test_step(self, data):
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            x, y = data[0], data[1]
        else:
            x, y = data[0], data[1]
        y = tf.cast(y, tf.float32)
        y_pred_mean, y_pred_log_var, kl_loss = self(x, training=False)

        loss_nll = 0.5 * y_pred_log_var + 0.5 * tf.square(y - y_pred_mean) / tf.exp(y_pred_log_var)
        loss_nll = tf.reduce_mean(loss_nll)
        sign_mismatch = -tf.tanh(y) * tf.tanh(y_pred_mean)
        loss_direction = tf.reduce_mean(tf.maximum(0.0, sign_mismatch))

        total_loss = loss_nll + self.beta * tf.reduce_mean(kl_loss) + 0.5 * loss_direction
        return {"loss": total_loss, "nll": loss_nll, "kl": self.kl_loss_tracker.result(), "direction": loss_direction}
