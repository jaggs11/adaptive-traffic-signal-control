import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

def main():
    df = pd.read_csv("data/processed/training_samples.csv")

    X = df[["queue_ns", "queue_ew", "wait_ns", "wait_ew", "phase_is_ns"]]
    y = df["target_green_duration"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, pred)
    print("Validation MAE:", mae)

    joblib.dump(model, "models/anfis_model.pkl")
    print("Saved model to models/anfis_model.pkl")

if __name__ == "__main__":
    main()