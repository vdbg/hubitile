from geofence import CircleFence, Point, PolygonFence
import logging


def test_circle() -> None:
    conf = {
        "latitude": 40.690080,
        "longitude": -74.045290,
        "radius": 200
    }

    liberty_island = CircleFence("statue of liberty", conf, None, None, None)

    statue_museum = Point(40.690471, -74.046599)
    ellis_island = Point(40.697466, -74.041202)
    pentagon = Point(38.871990, -77.054668)

    assert(liberty_island.isInside(statue_museum))
    assert(not liberty_island.isInside(ellis_island))
    assert(not liberty_island.isInside(pentagon))


def test_polygon_large() -> None:
    conf = {
        "vertices": [
            [46.999099, -121.914726],
            [46.993479, -121.536385],
            [46.779015, -121.453987],
            [46.736208, -121.528145],
            [46.739972, -121.910607]
        ]
    }

    mount_rainier = PolygonFence("Mount Rainier", conf, None, None, None)

    giant_falls = Point(46.903575, -121.834821)
    paradise = Point(46.786515, -121.736888)

    bearhead = Point(47.020129, -121.806625)
    puyallup = Point(47.163076, -122.283391)

    assert(mount_rainier.isInside(giant_falls))
    assert(mount_rainier.isInside(paradise))

    assert(not mount_rainier.isInside(bearhead))
    assert(not mount_rainier.isInside(puyallup))


def test_polygon_small() -> None:
    conf = {
        "vertices": [
            [46.786691, -121.734396],
            [46.787265, -121.733677],
            [46.786871, -121.733782],
            [46.786722, -121.733490],
            [46.786610, -121.733632],
            [46.786711, -121.733927],
            [46.786558, -121.734133],
            [46.786668, -121.734399]
        ]
    }
    paradise_inn = PolygonFence("Paradise Inn", conf, None, None, None)

    assert(paradise_inn.isInside(Point(46.786811, -121.734039)))
    assert(paradise_inn.isInside(Point(46.786693, -121.733634)))
    assert(not paradise_inn.isInside(Point(46.786614, -121.733282)))
    assert(not paradise_inn.isInside(Point(46.786512, -121.735368)))


logging.root.level = logging.DEBUG
test_circle()
test_polygon_large()
test_polygon_small()
