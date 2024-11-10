import tensorflow as tf

def analyze_sentiment(text, model):
    sentiment_score = model.predict([text])[0][0]
    return sentiment_score

def load_sentiment_model():
    try:
        return tf.keras.models.load_model("sentiment_model.h5")
    except Exception as e:
        print(f"Error loading sentiment model: {e}")
        return None
