import argparse
import logging
from datetime import datetime
from pathlib import Path

import lightgbm as lgb
import optuna

from constants import MODEL_FOLDER

logger = logging.getLogger(__name__)
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def retrain_and_save_best_model(
    best_trial: optuna.trial.FrozenTrial, target_folder: Path
) -> lgb.Booster:
    train_set = lgb.Dataset(target_folder / "lightgbm_train.bin")
    test_set_weekday = lgb.Dataset(target_folder / "lightgbm_test_weekday.bin")
    test_set_weekend = lgb.Dataset(target_folder / "lightgbm_test_weekend.bin")

    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "num_threads": 6,
        **best_trial.params,  # Unpack the best trial's hyperparameters
    }

    model = lgb.train(
        params,
        train_set,
        valid_sets=[test_set_weekday, test_set_weekend],
        valid_names=["weekday_test_set", "weekend_test_set"],
    )

    model_path = target_folder / f"{TIMESTAMP}_best_lgbm_model.txt"
    model.save_model(model_path)
    logger.info(f"Best model saved to {model_path}")

    return model


def objective(trial, target_folder: Path):
    train_set = lgb.Dataset(target_folder / "lightgbm_train.bin")
    test_set_weekday = lgb.Dataset(target_folder / "lightgbm_test_weekday.bin")
    test_set_weekend = lgb.Dataset(target_folder / "lightgbm_test_weekend.bin")

    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.5, log=True),
        "num_threads": 6,
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 1, 2000),
        "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 5.0),
        "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 5.0),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.7, 1.0),
        "num_leaves": trial.suggest_int("num_leaves", 255, 2047),
        "cat_smooth": trial.suggest_int("cat_smooth", 0, 20),
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

    target_folder: Path = MODEL_FOLDER / args.folder

    log_file = target_folder / "optuna_training.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    optuna.logging.set_verbosity(optuna.logging.INFO)
    logger.info("A new round of Optuna tuning has started.")

    study = optuna.create_study(directions=["minimize", "minimize"])
    study.optimize(
        lambda t: objective(t, target_folder), n_trials=500, show_progress_bar=True
    )

    logger.info(f"Number of finished trials: {len(study.trials)}")

    logger.info("Best trials on the Pareto Front:")
    for trial in study.best_trials:
        logger.info(f"  Trial ID: {trial.number}")
        logger.info(f"    Values (Weekday, Weekend): {trial.values}")
        logger.info(f"    Params: {trial.params}")

    # re-train and save the best model
    best_trial = min(study.best_trials, key=lambda t: sum(t.values) / len(t.values))
    logger.info(f"Selected trial {best_trial.number} with values {best_trial.values}")

    retrain_and_save_best_model(best_trial, target_folder)

    # save training plots for later inspection
    optuna.visualization.plot_optimization_history(study).write_html(
        target_folder / f"{TIMESTAMP}_optuna_optimization_history.html"
    )
    optuna.visualization.plot_param_importances(study).write_html(
        target_folder / f"{TIMESTAMP}_optuna_parameter_importance.html"
    )
    optuna.visualization.plot_pareto_front(study).write_html(
        target_folder / f"{TIMESTAMP}_pareto_front.html"
    )
    logger.info(f"Optuna diagnosis plots have been saved to {target_folder}")
