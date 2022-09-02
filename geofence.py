from datetime import datetime
import math
import logging
from typing import Optional

from hubitat import Hubitat
from pytile.tile import Tile


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
        return f"(lat={self.latitude};long={self.longitude})"

    def __eq__(self, other) -> bool:
        return self.longitude == other.longitude and self.latitude == other.latitude

    def __hash__(self) -> int:
        return hash(self.latitude) ^ hash(self.longitude)


class TileWrapper:
    def __init__(self, tile: Tile):
        self.tile = tile
        self.fullname = f"'{self.tile.name}' ({self.tile.uuid})"
        self.previously_ignored: bool = False
        self._location: Point = None

    async def refresh(self, api) -> None:
        self.tile._async_request = api._async_request
        await self.tile.async_update()
        self._location = None

    def __str__(self) -> str:
        return self.fullname

    @property
    def location(self) -> Point:
        if not self._location:
            self._location = Point(longitude=self.tile.longitude, latitude=self.tile.latitude)
        return self._location

    @property
    def last_timestamp(self) -> Optional[datetime]:
        return self.tile.last_timestamp

    @property
    def name(self) -> str:
        return self.tile.name

    @property
    def uuid(self) -> str:
        return self.tile.uuid


class GeoConfig:
    def __init__(self, hubitat_devices: dict[int, str]) -> None:
        self.all_tiles: set[str] = set()
        self.hubitatIds: set[int] = set()
        self.hubitat_devices = hubitat_devices


class Geofence:

    def __init__(self, name: str, conf: dict, geoconf: GeoConfig, exclusion: bool) -> None:
        self.name = name
        self.exclusion = exclusion
        key = "tiles"

        if key not in conf:
            logging.warn(f"No tiles associated with location '{name}'.")
            return

        self.tiles = {x: None for x in conf[key]} if exclusion else conf[key]

        for tile, hubitatId in self.tiles.items():
            geoconf.all_tiles.add(tile)
            if hubitatId is None:
                continue
            hubitatId = int(hubitatId)
            if hubitatId in geoconf.hubitatIds:
                raise Exception(f"Hubitat device Id {hubitatId} is referenced in location '{self}' and another location.")
            geoconf.hubitatIds.add(hubitatId)
            if hubitatId not in geoconf.hubitat_devices:
                raise Exception(f"Hubitat device Id {hubitatId} is not a virtual presence sensor exported by Hubitat's MakerAPI.")

    def __str__(self) -> str:
        return self.name

    def isInside(self, p: Point) -> bool:
        return False

    def processTile(self, tile: TileWrapper, hubitat: Hubitat) -> bool:
        key: str = None
        if tile.name in self.tiles:
            key = tile.name
        if tile.uuid in self.tiles:
            if key:
                raise Exception(f"Tile {tile} is referenced both by name and uuid in location '{self}'")
            key = tile.uuid
        if not key:
            logging.debug(f"Skipping tile {tile}.")
            return False

        inside = self.isInside(tile.location)
        logging.debug(f"Tile {tile} at {tile.location} is {'INSIDE' if inside else 'OUTSIDE'} location '{self}'")
        if not self.exclusion:
            hubitat.set_presence(id=self.tiles[key], arrived=inside)

        return inside


class PolygonFence(Geofence):
    def __init__(self, name: str, conf: dict, geoconf: GeoConfig, exclusion: bool) -> None:
        super().__init__(name, conf, geoconf, exclusion)

        vertices: list[list[float]] = conf.get("vertices", [])
        hashes: set[Point] = set()

        if len(vertices) < 3:
            raise Exception(f"Polygon fence '{self}' needs at least 3 vertices.")

        self.p: list[Point] = []

        for data in vertices:
            if len(data) != 2:
                raise Exception(f"Invalid (lat,long) pair: {data}.")
            point = Point(data[0], data[1])
            if point in hashes:
                raise Exception(f"Vertex {point} used twice in '{self}'.")
            hashes.add(point)

            self.p.append(point)

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
    def __init__(self, name: str, conf: dict, geoconf: GeoConfig, exclusion: bool) -> None:
        super().__init__(name, conf, geoconf, exclusion)
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
        logging.debug(f"Distance to '{self}': {distance} m")
        return distance <= self.radius


class Geofences:
    def __init__(self, conf: dict, hubitat_devices: dict[int, str]) -> None:
        self.geoconf = GeoConfig(hubitat_devices)
        self.geofences = self._get_geofences(conf, "geofences", False)
        self.exclusions = self._get_geofences(conf, "exclusions", True)

    def _get_geofences(self, rootConf: dict, key: str, exclusion: bool) -> list[Geofence]:
        ret = []
        if key not in rootConf:
            return ret
        conf = rootConf[key]
        if not conf:
            return ret
        if "circles" in conf:
            for name, data in conf["circles"].items():
                ret.append(CircleFence(name, data, self.geoconf, exclusion))

        if "polygons" in conf:
            for name, data in conf["polygons"].items():
                ret.append(PolygonFence(name, data, self.geoconf, exclusion))

        return ret

    def handlesTile(self, tile: TileWrapper) -> bool:
        return tile.name in self.geoconf.all_tiles or tile.uuid in self.geoconf.all_tiles

    def evaluate(self, tile: TileWrapper, hubitat: Hubitat) -> bool:
        for geofence in self.exclusions:
            if geofence.processTile(tile, hubitat):
                if not tile.previously_ignored:
                    logging.info(f"Ignoring tile {tile} in exclusion geofence '{geofence}'.")
                    tile.previously_ignored = True
                return
        tile.previously_ignored = False
        for geofence in self.geofences:
            geofence.processTile(tile, hubitat)
