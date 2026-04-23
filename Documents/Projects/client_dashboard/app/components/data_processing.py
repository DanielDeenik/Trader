import pandas as pd

class DataProcessor:
    def process_data(self, data):
        # Example processing logic; adapt as needed
        df = pd.DataFrame(data)
        df['processed'] = df.apply(lambda x: x.sum(), axis=1)
        return df
