import os
import pandas as pd

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_df(df: pd.DataFrame, path: str):
    ensure_dir(os.path.dirname(path))
    df.to_csv(path, index=False)