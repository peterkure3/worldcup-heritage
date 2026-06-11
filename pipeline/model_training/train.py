import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss
from sklearn.preprocessing import LabelEncoder

import xgboost as xgb
import lightgbm as lgb
import optuna

FEATURES_DIR = Path(__file__).resolve().parent.parent / "data" / "features"
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "models"

FEATURE_COLS = [
    "home_form_gf", "home_form_ga", "home_form_pts",
    "away_form_gf", "away_form_ga", "away_form_pts",
    "h2h_home_win_rate", "h2h_away_win_rate", "h2h_draw_rate",
    "knockout",
]
TARGET = "target"


def load_features() -> pd.DataFrame:
    path = FEATURES_DIR / "training_features.parquet"
    df = pd.read_parquet(path)
    df[TARGET] = df[["target_home_win", "target_draw", "target_away_win"]].idxmax(axis=1)
    df[TARGET] = df[TARGET].map({"target_home_win": 0, "target_draw": 1, "target_away_win": 2})
    return df


def split_time_series(df: pd.DataFrame, test_seasons: list[int]):
    train = df[~df["season"].isin(test_seasons)].copy()
    test = df[df["season"].isin(test_seasons)].copy()
    return train, test


def train_baseline(X_train, y_train, X_test, y_test) -> dict:
    model = LogisticRegression(max_iter=1000, solver="lbfgs")
    model.fit(X_train, y_train)
    preds = model.predict_proba(X_test)
    return {
        "model": model,
        "log_loss": log_loss(y_test, preds),
        "accuracy": accuracy_score(y_test, preds.argmax(axis=1)),
    }


def train_xgboost(X_train, y_train, X_test, y_test, params=None) -> dict:
    if params is None:
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "seed": 42,
        }
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)
    model = xgb.train(params, dtrain, num_boost_round=200, evals=[(dtest, "test")], early_stopping_rounds=20, verbose_eval=False)
    preds = model.predict(dtest)
    return {
        "model": model,
        "log_loss": log_loss(y_test, preds),
        "accuracy": accuracy_score(y_test, preds.argmax(axis=1)),
    }


def train_lightgbm(X_train, y_train, X_test, y_test, params=None) -> dict:
    if params is None:
        params = {
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.1,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "seed": 42,
            "verbose": -1,
        }
    ltrain = lgb.Dataset(X_train, label=y_train)
    ltest = lgb.Dataset(X_test, label=y_test, reference=ltrain)
    model = lgb.train(params, ltrain, num_boost_round=200, valid_sets=[ltest], callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)])
    preds = model.predict(X_test)
    return {
        "model": model,
        "log_loss": log_loss(y_test, preds),
        "accuracy": accuracy_score(y_test, preds.argmax(axis=1)),
    }


def tune_xgboost(df_train, df_test) -> dict:
    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[TARGET].values
    X_test = df_test[FEATURE_COLS].values
    y_test = df_test[TARGET].values

    def objective(trial):
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "seed": 42,
        }
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtest = xgb.DMatrix(X_test, label=y_test)
        model = xgb.train(params, dtrain, num_boost_round=200, evals=[(dtest, "test")], early_stopping_rounds=20, verbose_eval=False)
        preds = model.predict(dtest)
        return log_loss(y_test, preds)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=30, show_progress_bar=False)

    return study.best_params


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading features...")
    df = load_features()
    print(f"  {len(df)} samples, {len(FEATURE_COLS)} features")

    # Time-series split: train on 1998-2014, test on 2018+2022
    train, test = split_time_series(df, test_seasons=[2018, 2022])
    print(f"  Train: {len(train)} (seasons {train['season'].min()}-{train['season'].max()})")
    print(f"  Test:  {len(test)} (seasons {test['season'].min()}-{test['season'].max()})")

    X_train = train[FEATURE_COLS].values
    y_train = train[TARGET].values
    X_test = test[FEATURE_COLS].values
    y_test = test[TARGET].values

    print("\n--- Baseline: Logistic Regression ---")
    baseline = train_baseline(X_train, y_train, X_test, y_test)
    print(f"  Log-loss: {baseline['log_loss']:.4f}, Accuracy: {baseline['accuracy']:.3f}")

    print("\n--- XGBoost (default params) ---")
    xgb_result = train_xgboost(X_train, y_train, X_test, y_test)
    print(f"  Log-loss: {xgb_result['log_loss']:.4f}, Accuracy: {xgb_result['accuracy']:.3f}")
    joblib.dump(xgb_result["model"], MODELS_DIR / "xgboost_v1.joblib")
    print(f"  Saved → {MODELS_DIR / 'xgboost_v1.joblib'}")

    print("\n--- LightGBM (default params) ---")
    lgb_result = train_lightgbm(X_train, y_train, X_test, y_test)
    print(f"  Log-loss: {lgb_result['log_loss']:.4f}, Accuracy: {lgb_result['accuracy']:.3f}")
    joblib.dump(lgb_result["model"], MODELS_DIR / "lightgbm_v1.joblib")
    print(f"  Saved → {MODELS_DIR / 'lightgbm_v1.joblib'}")

    print("\n--- XGBoost Hyperparameter Tuning (Optuna) ---")
    best_params = tune_xgboost(train, test)
    print(f"  Best params: {best_params}")

    print("\n--- XGBoost (tuned) ---")
    xgb_tuned = train_xgboost(X_train, y_train, X_test, y_test, params={
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "seed": 42,
        **best_params,
    })
    print(f"  Log-loss: {xgb_tuned['log_loss']:.4f}, Accuracy: {xgb_tuned['accuracy']:.3f}")
    joblib.dump(xgb_tuned["model"], MODELS_DIR / "xgboost_v1_tuned.joblib")
    print(f"  Saved → {MODELS_DIR / 'xgboost_v1_tuned.joblib'}")

    print("\nDone.")


if __name__ == "__main__":
    main()
