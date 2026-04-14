import argparse
import logging
import optuna
import lightgbm as lgb
from constants import MODEL_FOLDER

logger = logging.getLogger(__name__)


def objective(trial, target_folder):
    train_set = lgb.Dataset(target_folder / "lightgbm_train.bin")
    test_set_weekday = lgb.Dataset(target_folder / "lightgbm_test_weekday.bin")
    test_set_weekend = lgb.Dataset(target_folder / "lightgbm_test_weekend.bin")

    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.2, log=True),
        "num_threads": 6,
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 20),
        "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 3.0),
        "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 3.0),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.7, 1.0),
        "num_leaves": trial.suggest_int("num_leaves", 127, 511),
        "cat_smooth": trial.suggest_int("cat_smooth", 5, 10),
    }

    model = lgb.train(
        params,
        train_set,
        valid_sets=[test_set_weekday, test_set_weekend],
        valid_names=["weekday_test_set", "weekend_test_set"],
    )

    return model.best_score["weekday_test_set"]["rmse"], model.best_score[
        "weekend_test_set"
    ]["rmse"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    target_folder = MODEL_FOLDER / args.folder

    log_file = target_folder / "optuna_training.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(directions=["minimize", "minimize"])

    study.optimize(
        lambda t: objective(t, target_folder), n_trials=100, show_progress_bar=True
    )

    logger.info(f"Number of finished trials: {len(study.trials)}")

    logger.info("Best trials on the Pareto Front:")
    for trial in study.best_trials:
        logger.info(f"  Trial ID: {trial.number}")
        logger.info(f"    Values (Weekday, Weekend): {trial.values}")
        logger.info(f"    Params: {trial.params}")
