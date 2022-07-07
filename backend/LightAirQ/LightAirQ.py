from datetime import datetime, timedelta
from math import asin, cos
from math import pow as math_pow
from math import radians, sin, sqrt
from typing import List, Tuple

import requests
from loguru import logger
from requests.structures import CaseInsensitiveDict

from .exceptions import (AllStationsOfflineError, DecodingError, GetMeasurementError, GetPostsError,
                         HaversineFormulaError, RequestException, SendRequestError, StatusCodeError)

DEFAULT_HOST = "https://api.cityscreen.io"
POSTS_URL = "harvester/v2/Posts"
MEASUREMENTS_URL = "harvester/v2/Posts/measurements"
TIMEOUT = 10


class LightAirQ:
    """Object for accessing data of CityAir project."""

    def __init__(self, token: str, host_url: str = DEFAULT_HOST, timeout: int = TIMEOUT):
        """Initialize class.

        Args:
            token (str): CitiAir access token
            host_url (str, optional): Url of the CityAir API
            timeout (int, optional): Timeout for the server request. Defaults to 10
        """
        self.__host_url = host_url
        self.__timeout = timeout

        self.__headers = CaseInsensitiveDict()
        self.__headers["Content-Type"] = "application/json"
        # self.__headers["Connection"] = "keep-alive"
        self.__headers["Authorization"] = f"Bearer {token}"

        self.__session = requests.Session()
        self.__session.headers = self.__headers

    def __haversine(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """https://en.wikipedia.org/wiki/Haversine_formula.

            Args:
                point1 (Tuple): Latitude and longitude of the first point
                point2 (Tuple): Latitude and longitude of the second point

            Raises:
                HaversineFormulaError: Called when a calculation error occurs

            Returns:
                float: Distance in kilometers between points
            """
        try:

            latitude1, longitude1 = radians(point1[0]), radians(point1[1])
            latitude2, longitude2 = radians(point2[0]), radians(point2[1])

            dlat = latitude2 - latitude1
            dlon = longitude2 - longitude1

            hav = math_pow(sin(dlat / 2), 2) + cos(latitude1) * cos(latitude2) * math_pow(sin(dlon / 2), 2)

            distance_km = 6371 * 2 * asin(sqrt(hav))

            if distance_km < 0:
                raise ValueError

            return distance_km

        except (TypeError, ValueError) as err:
            logger.error(HaversineFormulaError(point1, point2, err))
            raise HaversineFormulaError

        except Exception:
            logger.exception("Unknown exception")
            raise

    def __make_request(self, method_url: str, **kwargs: object) -> dict | List[dict]:
        """Make request to CityAir backend.

        Args:
            method_url (str): Url of the specified method

        Raises:
            SendRequestError: Called when an error occurs while sending a request.
            StatusCodeError: Called when an invalid status code is received from the server
            DecodingError: Called when a response decoding error occurs

        Returns:
            dict | List[dict]: Server answer
        """
        params = {}
        url = ""

        try:
            params = {**kwargs}
            url = f"{self.__host_url}/{method_url}"

            response = self.__session.get(url, params=params, timeout=self.__timeout)
            response.raise_for_status()
            response_json = response.json()

            if not response_json:
                raise requests.HTTPError

            return response_json

        except requests.HTTPError as err:
            logger.exception(StatusCodeError(params, url, response.status_code, response.text))
            raise StatusCodeError(params, url, response.status_code, response.text) from err

        except requests.RequestException as err:
            logger.exception(SendRequestError(params, url))
            raise SendRequestError(params, url) from err

        except requests.JSONDecodeError as err:
            logger.exception(DecodingError(params, url, response.status_code, response.text))
            raise DecodingError(params, url, response.status_code, response.text) from err

        except Exception:
            logger.exception("Unknown exception")
            raise

    def get_available_posts(self) -> List[dict]:
        """Get a list of available posts.

        Raises:
            GetPostsError: Called when a data processing error occurs

        Returns:
            List[dict]: List of available posts
        """
        try:
            posts = self.__make_request(POSTS_URL)

            for post in posts:
                for dict_key, dict_value in post.pop("geo").items():
                    post[dict_key] = dict_value

            return posts

        except RequestException:
            raise

        except (TypeError, AttributeError, KeyError) as err:
            logger.exception(GetPostsError(posts))
            raise GetPostsError(posts) from err

        except Exception:
            logger.exception("Unknown exception")
            raise

    def get_nearest_station(self, posts: List[dict], reference_point: Tuple[float, float]) -> List[dict]:
        """Sort posts by ascending distance.

        Args:
            posts (List[dict]): List of available posts
            reference_point (Tuple): Latitude and longitude of reference point

        Raises:
            SortPostsError: Called when a data processing error occurs

        Returns:
            List[dict]: List of posts in order of increasing distance from the reference point
        """
        try:

            posts: list = list(filter(lambda post: post["isOnline"] and post["latitude"] and post["longitude"], posts))

            if not posts:
                raise AllStationsOfflineError

            min_index: int = 0
            min_distance: int = 10**5

            for index, post in enumerate(posts):

                try:
                    distance: float = self.__haversine(reference_point, (post["latitude"], post["longitude"]))
                    # print(post["id"], distance)

                except HaversineFormulaError:
                    continue

                if distance < min_distance:
                    min_distance = distance
                    min_index = index

            return posts[min_index], min_distance

        except AllStationsOfflineError:
            logger.error(AllStationsOfflineError)
            raise AllStationsOfflineError

        except Exception:
            logger.exception("Unknown exception")
            raise

    def get_last_measurement_from_post(self, post_id: int) -> dict:
        """Request the latest measurement from the post, averaged over five minutes.

        Args:
            post_id (int): Шd of the post from which data will be requested

        Returns:
            Optional[dict]: Post measurements
        """
        try:
            date__gt = datetime.utcnow()
            date__gt = date__gt.replace(minute=(date__gt.minute // 5) * 5, second=0,
                                        microsecond=0) - timedelta(minutes=5)

            measurements = self.__make_request(
                MEASUREMENTS_URL,
                ids=post_id,
                interval="5m",
                date__gt=date__gt,
                limit=2,
                measure_scheme="c_mmhg_mg",
            )

            measurements_units = measurements["meta"]["units"]

            measurements_data = measurements["data"][-1]

            measurements_data["cityairAqi"] = measurements_data.pop("aqi")["cityairAqi"]["value"]

            for dict_key, dict_value in measurements_data.items():
                if dict_key in measurements_units:
                    measurements_data[dict_key] = f"{dict_value} {measurements_units[dict_key]}"

            return measurements_data

        except RequestException:
            raise

        except (AttributeError, IndexError, KeyError) as err:
            logger.exception(GetMeasurementError(measurements))
            raise GetMeasurementError(measurements) from err

        except Exception:
            logger.exception("Unknown exception")
            raise
