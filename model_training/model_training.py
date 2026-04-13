import argparse
import logging

import optuna
import optuna_integration.lightgbm as lgb
from lightgbm import early_stopping, log_evaluation

from constants import MODEL_FOLDER


def main():
    # specify the folder in which the data is and the final model should be saved
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    subfolder_name: str = args.folder

    TARGET_FOLDER = MODEL_FOLDER / subfolder_name

    # check if required data are in the specified folder location
    required_files = ["lightgbm_train.bin", "lightgbm_test.bin"]
    missing = [f for f in required_files if not (TARGET_FOLDER / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files in {TARGET_FOLDER}: {missing}")

    LOG_FILE = TARGET_FOLDER / "optuna_training.log"

    # Load datasets
    train_set = lgb.Dataset(TARGET_FOLDER / "lightgbm_train.bin")
    test_set = lgb.Dataset(TARGET_FOLDER / "lightgbm_test.bin")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE)],
    )
    logger = logging.getLogger(__name__)

    # Suppress fragmented progress bar output from LightGBM/Optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_threads": 6,
    }

    study = optuna.create_study(direction="minimize")

    tuner = lgb.LightGBMTuner(
        params=params,
        train_set=train_set,
        num_boost_round=5000,
        valid_sets=[test_set],
        valid_names=["test"],
        callbacks=[
            early_stopping(stopping_rounds=25, min_delta=0.003),
            log_evaluation(period=0),
        ],
        study=study,
        show_progress_bar=True,
        model_dir=str(TARGET_FOLDER / "tuner_checkpoints"),
    )

    tuner.run()

    # save best models
    best_model = tuner.get_best_booster()
    best_model.save_model(str(TARGET_FOLDER / "best_lgbm_model.txt"))

    logger.info("Best RMSE: %s", tuner.best_score)
    logger.info("Model saved to: %s", TARGET_FOLDER / "best_lgbm_model.txt")


if __name__ == "__main__":
    main()
