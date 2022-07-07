# from datetime import datetime
import os
from datetime import datetime

import aiofiles
import orjson
from fastapi import APIRouter, Query
from fastapi import status as status_code
from fastapi.responses import ORJSONResponse
from LightAirQ import LightAirQ

stations_router = APIRouter(tags=["stations"])

# API access token
TOKEN = os.environ["TOKEN"]

STATION_CACHE = ".cache/station.json"
MEASUREMENT_CACHE = ".cache/measurement.json"
STATION_TIMESTAMP_FIELD = "timestamp"
STATION_FILED = "stations"
POSTID_FIELD = "postId"
MEASUREMENT_TIMESTAMP_FIELD = "date"

airq = LightAirQ(TOKEN)


async def station_cache_uptime(utc_timestamp: int) -> (bool, dict):

    if not os.path.exists(STATION_CACHE):
        with open(STATION_CACHE, "w"):
            pass

    async with aiofiles.open(STATION_CACHE, "rb") as file:
        station_data: bytes = await file.read()

    if not station_data:
        return False, {}

    station_data: dict = orjson.loads(station_data)
    station_data_timestamp: int | None = station_data.get(STATION_TIMESTAMP_FIELD)

    if not station_data_timestamp:
        return False, {}

    time_delta: int = utc_timestamp - station_data_timestamp

    if time_delta > 600:
        return False, {}

    return True, station_data[STATION_FILED]


async def measurement_cache_uptime(utc_timestamp: int, post_id: int) -> (bool, dict):

    if not os.path.exists(MEASUREMENT_CACHE):
        with open(MEASUREMENT_CACHE, "w"):
            pass

    async with aiofiles.open(MEASUREMENT_CACHE, "rb") as file:
        raw_measurement_data: bytes = await file.read()

    if not raw_measurement_data:
        return False, {}

    raw_measurement_data: dict = orjson.loads(raw_measurement_data)

    measurement_data = raw_measurement_data.get(str(post_id))

    if not measurement_data:
        return False, raw_measurement_data

    measurement_data_timestamp: int = measurement_data.get(MEASUREMENT_TIMESTAMP_FIELD)
    time_delta: int = utc_timestamp - int(datetime.fromisoformat(measurement_data_timestamp[:-1]).timestamp())

    if time_delta >= 300:
        return False, raw_measurement_data

    return True, measurement_data


@stations_router.get("/nearest")
async def get_nearest_station_by_location(latitude: float = Query(ge=-90, le=90),
                                          longitude: float = Query(ge=-180, le=180)):

    utc_timestamp = int(datetime.utcnow().timestamp())

    if not os.path.exists(MEASUREMENT_CACHE):
        with open(MEASUREMENT_CACHE, "w"):
            pass

    station_cache = await station_cache_uptime(utc_timestamp)

    if station_cache[0]:
        stations = station_cache[1]
        print("Stations cache available - using it")

    else:
        stations = airq.get_available_posts()

        data = {STATION_FILED: stations, STATION_TIMESTAMP_FIELD: utc_timestamp}

        async with aiofiles.open(STATION_CACHE, "wb") as file:
            await file.write(orjson.dumps(data))

        print("Station cache old or non exists - create it and use", datetime.now())

    nearest_station = airq.get_nearest_station(stations, (latitude, longitude))

    nearest_station_id = nearest_station[0]["id"]

    measurement_cache = await measurement_cache_uptime(utc_timestamp, nearest_station_id)

    if measurement_cache[0]:
        measurement = measurement_cache[1]
        print("Measurement cache available - using it")

    else:
        measurement = airq.get_last_measurement_from_post(nearest_station_id)

        data = measurement_cache[1]

        data[str(nearest_station_id)] = measurement

        async with aiofiles.open(MEASUREMENT_CACHE, "wb") as file:
            await file.write(orjson.dumps(data))

        print("Measurement cache old or non exists - create it and use", datetime.now())

    return ORJSONResponse(content=measurement, status_code=status_code.HTTP_200_OK)
