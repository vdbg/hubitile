import asyncio
import time
import logging
from pathlib import Path
import yaml


from geofence import Geofences
from hubitat import Hubitat
from tile import Tiles

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

try:
    with open(Path(__file__).with_name("config.yaml")) as config_file:

        config = yaml.safe_load(config_file)

        if not config:
            raise ValueError("Invalid config.yaml. See template.config.yaml.")

        for name in {"tile", "main", "geofences", "hubitat"}:
            if name not in config:
                raise ValueError(f"Invalid config.yaml: missing section {name}.")

        main_conf = config["main"]
        logging.getLogger().setLevel(logging.getLevelName(main_conf["logverbosity"]))
        loop_seconds: int = int(main_conf["loop_seconds"])

        hubitat = Hubitat(config["hubitat"])
        geofences = Geofences(config, hubitat.get_all_devices())
        tiles = Tiles(config["tile"], geofences, hubitat)

        asyncio.run(tiles.discover())
        tiles.update_hubitat()

        while True:
            time.sleep(loop_seconds)
            logging.debug("Refreshing tiles.")
            asyncio.run(tiles.refresh())


except FileNotFoundError as e:
    logging.error("Missing config.yaml file.")
    exit(2)

except Exception as e:
    logging.exception(e)
    exit(1)
