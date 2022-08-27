[![GitHub issues](https://img.shields.io/github/issues/vdbg/hubitile.svg)](https://github.com/vdbg/hubitile/issues)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/vdbg/hubitile/main/LICENSE)

# HubiTile: Hubitat Tile integration

This program allows for associating [Tile](http://www.tile.com/) trackers with [Hubitat](https://hubitat.com/)
virtual presence devices corresponding to [geofences](https://en.wikipedia.org/wiki/Geo-fence).

## Highlights

* Can track any number `n` of tiles from a given Tile account.
* Can have any number `g` of geofences. This translates to `n*g` virtual presence sensors in Hubitat.
* Geofences can be entered as circles or complex polygons.

## Lowlights

* Freshness of the signal depends both on a device (typically a phone with the Tile app installed) to see the Tile device and on how often this app calls the Tile cloud APIs.
* Accuracy is not always great. The position reported by the Tile APIs is the position of the **phone** when reported to the Tile backend it was within Bluetooth range of the Tile device, and not of the position of the Tile device itself. For example, any person with the Tile app installed on their phone driving past your house could detect the Tile sensor which would "move" the last Tile device location detected to somewhere on the road. If the Tile app is slow to report the position, then the Tile device will be reported as even further away down the road.

## Pre-requisites

* A [Hubitat](https://hubitat.com/) hub.
* A device, capable of running either Docker containers or Python, that is on the same LAN as the hub e.g., [Rasbpian](https://www.raspbian.org/) or Windows.
* [Maker API](https://docs.hubitat.com/index.php?title=Maker_API) app installed and configured in Hubitat.
* A `Virtual Presence` device created in Hubitat for each pair of (geofence, tile_sensor) that the app should update.
* All of these virtual presence sensors are exported in Maker API.

## Installing

Choose one of these 3 methods.

### Using pre-built Docker image

1. `touch config.yaml`
2. This will fail due to malformed config.yaml. That's intentional :)  
   ``sudo docker run --name my_hubitile -v "`pwd`/config.yaml:/app/config.yaml" vdbg/hubitile``
3. `sudo docker cp my_hubitile:/app/template.config.yaml config.yaml`
4. Edit `config.yaml` by following the instructions in the file
5. `sudo docker start my_hubitile -i`  
  This will display logging on the command window allowing for rapid troubleshooting. `Ctrl-C` to stop the container if `config.yaml` is changed
7. When done testing the config:
  * `sudo docker container rm my_hubitile`
  * ``sudo docker run -d --name my_hubitile -v "`pwd`/config.yaml:/app/config.yaml" --restart=always --memory=100m vdbg/hubitile``
  * To see logs: `sudo docker container logs -f my_hubitile`

### Using Docker image built from source

1. `git clone https://github.com/vdbg/hubitile.git`
2. `sudo docker build -t hubitile_image hubitile`
3. `cd hubitile`
4. `cp template.config.yaml config.yaml` 
5. Edit `config.yaml` by following the instructions in the file
6. Test run: ``sudo docker run --name my_hubitile -v "`pwd`/config.yaml:/app/config.yaml" hubitile_image``  
   This will display logging on the command window allowing for rapid troubleshooting. `Ctrl-C` to stop the container if `config.yaml` is changed
7. If container needs to be restarted for testing: `sudo docker start my_hubitile -i` 
8. When done testing the config:
  * `sudo docker container rm my_hubitile`
  * ``sudo docker run -d --name my_hubitile -v "`pwd`/config.yaml:/app/config.yaml" --restart=always --memory=100m hubitile_image``
  * To see logs: `sudo docker container logs -f my_hubitile`

### Running directly on the device

[Python](https://www.python.org/) 3.9 or later with pip3 required.

To install:

1. `git clone https://github.com/vdbg/hubitile.git`
2. `cd hubitile`
3. `cp template.config.yaml config.yaml`
4. Edit `config.yaml` by following the instructions in the file
5. `pip3 install -r requirements.txt` 
6. Run the program:
  * Interactive mode: `python3 main.py`
  * Shorter: `.\main.py` (Windows) or `./main.py` (any other OS).
  * As a background process (on non-Windows OS): `python3 main.py > log.txt 2>&1 &`
7. To exit: `Ctrl-C` if running in interactive mode, `kill` the process otherwise.

## Troubleshooting

* Set `main:logverbosity` to `DEBUG` in `config.yaml` to get more details. Note: **Hubitat's token is printed in plain text** when `main:logverbosity` is `DEBUG`
* Ensure the device running the Python script can access the Hubitat's Maker API by trying to access the `<hubitat:url>/apps/api/<hubitat:appid>/devices?access_token=<hubitat:token>` url from that device (replace placeholders with values from config.yaml)

## Authoring

Style:

* From command line: `pip3 install black`,
* In VS code: Settings,
    * Text Editor, Formatting, Format On Save: checked
    * Python, Formatting, Provider: `black`
    * Python, Formatting, Black Args, Add item: `--line-length=200`
