import argparse
import asyncio
import logging
from typing import Text, Optional

import rasa.utils.io
import rasa.train
from examples.restaurantbot.policy import RestaurantPolicy
from rasa.core.agent import Agent
from rasa.core.interpreter import RasaNLUInterpreter
from rasa.core.policies.memoization import MemoizationPolicy
from rasa.core.policies.mapping_policy import MappingPolicy

logger = logging.getLogger(__name__)


async def parse(core_model_path, nlu_model_path, text):
    interpreter = RasaNLUInterpreter(nlu_model_path, config_file="config.yml")

    agent = Agent.load(core_model_path, interpreter=interpreter)

    response = await agent.handle_text(text)

    logger.info("Text: '{}'".format(text))
    logger.info("Response:")
    logger.info(response)

    return response


async def train_core(
    domain_file: Text = "domain.yml",
    model_path: Text = "models/core",
    training_data_file: Text = "data/stories.md",
):
    agent = Agent(
        domain_file,
        policies=[
            MemoizationPolicy(max_history=3),
            MappingPolicy(),
            RestaurantPolicy(batch_size=100, epochs=400, validation_split=0.2),
        ],
    )

    training_data = await agent.load_data(training_data_file)
    agent.train(training_data)

    # Attention: agent.persist stores the model and all meta data into a folder.
    # The folder itself is not zipped.
    agent.persist(model_path)

    logger.info("Model trained. Stored in '{}'.".format(model_path))

    return model_path


def train_nlu(
    config_file="config.yml", model_path="models/nlu", training_data_file="data/nlu.md"
):
    from rasa.nlu.training_data import load_data
    from rasa.nlu import config
    from rasa.nlu.model import Trainer

    training_data = load_data(training_data_file)
    trainer = Trainer(config.load(config_file))
    trainer.train(training_data)

    # Attention: trainer.persist stores the model and all meta data into a folder.
    # The folder itself is not zipped.
    model_directory = trainer.persist(model_path)

    logger.info("Model trained. Stored in '{}'.".format(model_path))

    return model_directory


if __name__ == "__main__":
    rasa.utils.io.configure_colored_logging(loglevel="INFO")

    parser = argparse.ArgumentParser(description="Start the bot.")

    parser.add_argument(
        "--nlu-model-path", default="models/nlu/default", help="Path to the nlu model."
    )
    parser.add_argument(
        "--core-model-path", default="models/core", help="Path to the core model."
    )
    parser.add_argument("--text", default="hello", help="Text to parse.")

    parser.add_argument(
        "task",
        choices=["train-nlu", "train-core", "parse"],
        help="What the bot should do - e.g. train or parse text?",
    )
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    # decide what to do based on first parameter of the script
    if args.task == "train-nlu":
        train_nlu()
    elif args.task == "train-core":
        loop.run_until_complete(train_core())
    elif args.task == "parse":
        loop.run_until_complete(
            parse(args.core_model_path, args.nlu_model_path, args.text)
        )
