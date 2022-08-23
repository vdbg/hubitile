from asyncio.proactor_events import _ProactorBasePipeTransport
from functools import wraps
from aiohttp import ClientSession

from pytile import async_login
from pytile.tile import Tile
from pytile.errors import TileError

import logging

from geofence import Geofences
from hubitat import Hubitat

# Code copied from
# https://pythonalgos.com/runtimeerror-event-loop-is-closed-asyncio-fix
"""fix yelling at me error"""


def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != 'Event loop is closed':
                raise
    return wrapper


_ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
"""fix yelling at me error end"""


class Tiles:
    def __init__(self, tile_conf: dict, geofences: Geofences, hubitat: Hubitat) -> None:
        self.user = tile_conf["username"]
        self.password = tile_conf["password"]
        self.geofences = geofences
        self.hubitat = hubitat
        self.tiles: set[Tile] = set()

    def update_hubitat(self) -> None:
        for tile in self.tiles:
            logging.debug(f"Evaluating geofences for tile {self.get_name(tile)} last updated on {tile.last_timestamp}.")
            self.geofences.evaluate(longitude=tile.longitude, latitude=tile.latitude, name=tile.name, uuid=tile.uuid, hubitat=self.hubitat)

    async def refresh(self) -> None:
        async with ClientSession() as session:
            try:
                api = await async_login(self.user, self.password, session)
                for tile in self.tiles:
                    tile._async_request = api._async_request
                    await tile.async_update()
            except TileError as err:
                logging.error(err)

        self.update_hubitat()

    async def discover(self) -> None:
        async with ClientSession() as session:
            try:
                api = await async_login(self.user, self.password, session)

                tiles = await api.async_get_tiles()

                for tile in tiles.values():
                    if tile.name in self.geofences.tiles or tile.uuid in self.geofences.tiles:
                        logging.info(f"Tracking tile {self.get_name(tile)}.")
                        self.tiles.add(tile)
                    else:
                        logging.warn(f"Not tracking tile {self.get_name(tile)}.")
            except TileError as err:
                logging.error(err)

    def get_name(self, tile: Tile) -> str:
        return f"'{tile.name}' ({tile.uuid})"
