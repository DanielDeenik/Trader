def extract_features(df, sentiment_model):
    df["sentiment_score"] = df["text"].apply(lambda x: analyze_sentiment(x, sentiment_model))
    df["mention_count"] = df["text"].str.count(r"\b\w+\b")
    df["word_count"] = df["text"].apply(lambda x: len(x.split()))
    return df
