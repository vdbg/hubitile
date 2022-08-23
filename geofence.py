# https://github.com/geopy/geopy
from geopy.distance import Distance
from geopy.point import Point
from geopy.distance import great_circle

import logging

from hubitat import Hubitat


class Geofence:

    def __init__(self, name: str, conf: dict, all_tiles: set[str], hubitatIds: set[int], hubitat_devices: dict[int, str]) -> None:
        self.name = name

        if "tile_to_hubitat" not in conf:
            logging.warn(f"No tiles or Hubitat devices associated with section '{name}'.")
            return

        self.tiles = conf["tile_to_hubitat"]

        for tile, hubitatId in self.tiles.items():
            all_tiles.add(tile)
            hubitatId = int(hubitatId)
            if hubitatId in hubitatIds:
                raise Exception(f"Hubitat device Id {hubitatId} is referenced in section '{name}' and another section.")
            hubitatIds.add(hubitatId)
            if hubitatId not in hubitat_devices:
                raise Exception(f"Hubitat device Id {hubitatId} is not a virtual presence sensor exported by Hubitat's MakerAPI.")

    def isInside(self, p: Point) -> bool:
        return False

    def processTile(self, p: Point, name: str, uuid: str, hubitat: Hubitat) -> None:
        key: str = None
        if name in self.tiles:
            key = name
        if uuid in self.tiles:
            if key:
                raise Exception(f"Tile '{name}' with uuid {uuid} is referenced both by name and uuid in geofence {self.name}")
            key = uuid
        if not key:
            logging.debug(f"Skipping tile  '{name}' with uuid {uuid}.")
            return

        hubitat.set_presence(id=self.tiles[key], arrived=self.isInside(p))


class CircleFence(Geofence):
    def __init__(self, name: str, conf: dict, all_tiles: set[str], hubitatIds: set[int], hubitat_devices: dict[int, str]) -> None:
        super().__init__(name, conf, all_tiles, hubitatIds, hubitat_devices)
        longitude: float = conf["longitude"]
        latitude: float = conf["latitude"]
        radius: int = conf["radius"]
        self.center = Point(latitude=latitude, longitude=longitude)
        logging.debug(f"CircleFence(name={name},lat={self.center.latitude},long={self.center.longitude},radius={radius}m)")
        self.radius = Distance(kilometers=radius / 1000)

    def isInside(self, p: Point) -> bool:
        distance = great_circle(self.center, p)
        logging.debug(f"Distance to {self.name}: {distance.m} m")
        return distance <= self.radius


class Geofences:
    def __init__(self, conf: dict, hubitat_devices: dict[int, str]) -> None:
        self.geofences: list[Geofence] = []
        self.tiles = set()
        self.hubitatIds = set()

        if "circles" in conf:
            for name, data in conf["circles"].items():
                self.geofences.append(CircleFence(name, data, self.tiles, self.hubitatIds, hubitat_devices))

    def evaluate(self, longitude: float, latitude: float, name: str, uuid: str, hubitat: Hubitat) -> bool:
        p: Point = Point(latitude=latitude, longitude=longitude)
        for geofence in self.geofences:
            geofence.processTile(p=p, name=name, uuid=uuid, hubitat=hubitat)
