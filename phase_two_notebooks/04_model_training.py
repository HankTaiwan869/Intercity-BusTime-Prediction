import json
import logging

import optuna
import optuna_integration.lightgbm as lgb
from lightgbm import early_stopping, log_evaluation

from constants import MODEL_FOLDER, PROCESSED_DATA_FOLDER

LOG_FILE = MODEL_FOLDER / "optuna_training.log"

# Load datasets
train_set = lgb.Dataset(PROCESSED_DATA_FOLDER / "lightgbm_train.bin")
test_set = lgb.Dataset(PROCESSED_DATA_FOLDER / "lightgbm_test.bin")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger(__name__)

# Suppress fragmented progress bar output from LightGBM/Optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Base params — LightGBMTuner will tune the rest stepwise
params = {
    "objective": "regression",
    "metric": "rmse",
    "verbosity": -1,
    "boosting_type": "gbdt",
    "learning_rate": 0.05,
}

study = optuna.create_study(direction="minimize")

tuner = lgb.LightGBMTuner(
    params=params,
    train_set=train_set,
    num_boost_round=5000,
    valid_sets=[test_set],
    valid_names=["test"],
    callbacks=[
        early_stopping(stopping_rounds=50, min_delta=0.003),
        log_evaluation(period=0),
    ],
    study=study,
    show_progress_bar=True,
    model_dir=str(MODEL_FOLDER / "tuner_checkpoints"),
)

tuner.run()

# --- SAVE RESULTS ---

# 1. Save best hyperparameters
best_params = tuner.best_params
logger.info("Best params: %s", best_params)
with open(MODEL_FOLDER / "best_params.json", "w") as f:
    json.dump(best_params, f, indent=4)

# 2. The tuner already saved the best booster — retrieve and re-save explicitly
best_model = tuner.get_best_booster()
best_model.save_model(str(MODEL_FOLDER / "best_lgbm_model.txt"))

best_score = tuner.best_score
logger.info("Best RMSE: %s", best_score)

print(f"Best RMSE: {best_score}")
print(f"Model saved to: {MODEL_FOLDER / 'best_lgbm_model.txt'}")
