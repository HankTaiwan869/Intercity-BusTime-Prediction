import logging
import lightgbm as lgb
import optuna
from constants import PROCESSED_DATA_FOLDER, MODEL_FOLDER
import json

LOG_FILE = MODEL_FOLDER / "optuna_training.log"

train = lgb.Dataset(PROCESSED_DATA_FOLDER / "lightgbm_train.bin")
test = lgb.Dataset(PROCESSED_DATA_FOLDER / "lightgbm_test.bin")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger(__name__)


def objective(trial):
    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "num_leaves": trial.suggest_int("num_leaves", 2, 256),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.1, log=True),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
        "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
        "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
        "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
    }

    evals_result = {}

    lgb.train(
        params=params,
        train_set=train,
        num_boost_round=1,
        valid_sets=[train, test],
        valid_names=["train", "test"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=0),  # to suppress lightgbm logging message
            lgb.record_evaluation(evals_result),
        ],
    )

    score = evals_result["test"]["rmse"][-1]

    logger.info(
        f"Trial {trial.number} finished with RMSE: {score:.4f}. Params: {trial.params}"
    )

    return score


study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100, show_progress_bar=True)

with open(MODEL_FOLDER / "best_params.json", "w") as f:
    json.dump(study.best_trial.params, f)

print(f"\nNumber of finished trials: {len(study.trials)}")
print(f"Best trial value: {study.best_trial.value}")
print("Best Params:", study.best_trial.params)
