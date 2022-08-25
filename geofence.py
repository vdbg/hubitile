import math
import logging

from hubitat import Hubitat


class Point:
    def __init__(self, latitude: float, longitude: float) -> None:
        longitude = float(longitude)
        latitude = float(latitude)
        if longitude < -180 or longitude > 180:
            raise Exception(f"Invalid longitude value {longitude}.")
        if latitude < -90 or latitude > 90:
            raise Exception(f"Invalid latitude value {latitude}.")

        self.latitude = latitude
        self.longitude = longitude
        self.projection = None

    # Copied from https://community.esri.com/t5/python-questions/lat-long-to-web-mercator/td-p/521492
    def getWebMercator(self) -> list[float]:
        if not self.projection:
            num = self.longitude * 0.017453292519943295
            x = 6378137.0 * num
            a = self.latitude * 0.017453292519943295
            x_mercator = x
            y_mercator = 3189068.5 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
            self.projection = x_mercator, y_mercator
        return self.projection

    def X(self) -> float:
        return self.getWebMercator()[0]

    def Y(self) -> float:
        return self.getWebMercator()[1]

    def __str__(self) -> str:
        return f"(lat={self.latitude}.long={self.longitude};x={self.X()},y={self.Y()})"


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


class PolygonFence(Geofence):
    def __init__(self, name: str, conf: dict, all_tiles: set[str], hubitatIds: set[int], hubitat_devices: dict[int, str]) -> None:
        super().__init__(name, conf, all_tiles, hubitatIds, hubitat_devices)

        vertices: list[list[float]] = conf.get("vertices", [])

        if len(vertices) < 3:
            raise Exception(f"Polygon fence '{self.name}' needs at least 3 vertices.")

        self.p: list[Point] = []

        for data in vertices:
            if len(data) != 2:
                raise Exception(f"Invalid (lat,long) pair: {data}")
            self.p.append(Point(data[0], data[1]))

    # Copied from http://alienryderflex.com/polygon/
    def pointInPolygon(self, x: float, y: float) -> bool:
        corners: int = len(self.p)
        i: int = 0
        j: int = corners - 1
        ret: bool = False

        while i < corners:
            if (self.p[i].Y() < y and self.p[j].Y() >= y or self.p[j].Y() < y and self.p[i].Y() >= y) and (self.p[i].X() <= x or self.p[j].X() <= x):
                ret ^= (self.p[i].X()+(y-self.p[i].Y())/(self.p[j].Y()-self.p[i].Y())*(self.p[j].X()-self.p[i].X()) < x)
            j = i
            i = i+1

        return ret

    def isInside(self, p: Point) -> bool:
        return self.pointInPolygon(p.X(), p.Y())


class CircleFence(Geofence):
    def __init__(self, name: str, conf: dict, all_tiles: set[str], hubitatIds: set[int], hubitat_devices: dict[int, str]) -> None:
        super().__init__(name, conf, all_tiles, hubitatIds, hubitat_devices)
        longitude: float = conf["longitude"]
        latitude: float = conf["latitude"]
        radius: int = conf["radius"]
        self.center = Point(latitude=latitude, longitude=longitude)
        logging.debug(f"CircleFence(name={name},lat={self.center.latitude},long={self.center.longitude},radius={radius}m)")
        self.radius = radius

    # Computed using https://en.wikipedia.org/wiki/Haversine_formula
    def getDistance(self, p1: Point, p2: Point) -> float:
        # convert to radians
        lonp1 = math.radians(p1.longitude)
        lonp2 = math.radians(p2.longitude)
        latp1 = math.radians(p1.latitude)
        latp2 = math.radians(p2.latitude)

        dlon = lonp2 - lonp1
        dlat = latp2 - latp1
        a = math.sin(dlat/2)**2 + math.cos(latp1) * math.cos(latp2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # https://en.wikipedia.org/wiki/Earth_radius
        return c * r * 1000  # return in meters

    def isInside(self, p: Point) -> bool:
        distance = self.getDistance(self.center, p)
        logging.debug(f"Distance to '{self.name}': {distance} m")
        return distance <= self.radius


class Geofences:
    def __init__(self, conf: dict, hubitat_devices: dict[int, str]) -> None:
        self.geofences: list[Geofence] = []
        self.tiles = set()
        self.hubitatIds = set()

        if "circles" in conf:
            for name, data in conf["circles"].items():
                self.geofences.append(CircleFence(name, data, self.tiles, self.hubitatIds, hubitat_devices))

        if "polygons" in conf:
            for name, data in conf["polygons"].items():
                self.geofences.append(PolygonFence(name, data, self.tiles, self.hubitatIds, hubitat_devices))

    def evaluate(self, p: Point, name: str, uuid: str, hubitat: Hubitat) -> bool:
        for geofence in self.geofences:
            geofence.processTile(p=p, name=name, uuid=uuid, hubitat=hubitat)
