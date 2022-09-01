from asyncio.proactor_events import _ProactorBasePipeTransport
from functools import wraps
from aiohttp import ClientSession

from pytile import async_login
from pytile.errors import TileError

import logging

from geofence import Geofences, TileWrapper
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
        self.tiles: set[TileWrapper] = set()

    def update_hubitat(self) -> None:
        for tile in self.tiles:
            logging.debug(f"Evaluating geofences for tile {tile.fullname} last updated on {tile.last_timestamp}.")
            self.geofences.evaluate(tile, self.hubitat)

    async def refresh(self) -> None:
        async with ClientSession() as session:
            try:
                api = await async_login(self.user, self.password, session)
                for tile in self.tiles:
                    await tile.refresh(api)
            except TileError as err:
                logging.error(err)

        self.update_hubitat()

    async def discover(self) -> None:
        async with ClientSession() as session:
            try:
                api = await async_login(self.user, self.password, session)

                tiles = await api.async_get_tiles()

                for tileData in tiles.values():
                    tile = TileWrapper(tileData)
                    if self.geofences.handlesTile(tile):
                        logging.info(f"Tracking tile {tile.fullname}.")
                        self.tiles.add(tile)
                    else:
                        logging.warn(f"Not tracking tile {tile.fullname}.")
            except TileError as err:
                logging.error(err)
