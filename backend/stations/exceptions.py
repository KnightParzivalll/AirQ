from typing import List, Tuple


class LightAirQException(Exception):
    """Base exception for LightAirQ."""


class DistanceException(LightAirQException):
    """Base exception for distance calculation errors."""


class HaversineFormulaError(DistanceException):
    """Error in calculating the distance using the Haversine formula."""

    def __init__(self, point1: Tuple[float, float], point2: Tuple[float, float], msg: str):
        """Initialize class.

        Args:
            point1 (Tuple): Latitude and longitude of the first point
            point2 (Tuple): Latitude and longitude of the second point
        """
        message = f"An error occurred when calculating the distance between points {point1} & {point2}\nMsg: {msg}"

        super().__init__(message)


class RequestException(LightAirQException):
    """Basic exception for request errors."""


class SendRequestError(RequestException):
    """Request sending error."""

    def __init__(self, params: dict, url: str):
        """Initialize class.

        Args:
            params (dict): Request params
            url (str): Request url
        """
        message = f"An error occurred while sending the request;\nParams: {params}\nUrl: {url}"
        super().__init__(message)


class StatusCodeError(RequestException):
    """The response from the server contains an invalid status code."""

    def __init__(self, params: dict, url: str, response_code: int, response_text: str):
        """Initialize class.

        Args:
            params (dict): Request params
            url (str): Request url
            response_code (int): Response code
            response_text (str): Response text
        """
        message = (f"Invalid status code received;\nParams: {params}\nUrl: {url}\nCode: {response_code}\n"
                   "Text: {response_text}")

        super().__init__(message)


class DecodingError(RequestException):
    """Decoding error."""

    def __init__(self, params: dict, url: str, response_code: int, response_text: str):
        """Initialize class.

        Args:
            params (dict): Request params
            url (str): Request url
            response_code (int): Response code
            response_text (str): Response text
        """
        message = (f"Couldn't decode the text into json;\nParams: {params}\nUrl: {url}\nCode: {response_code}\n"
                   "Text: {response_text}")

        super().__init__(message)


class DataTransformationException(LightAirQException):
    """Basic exception for data transformation."""


class GetPostsError(DataTransformationException):
    """Decoding error."""

    def __init__(self, data: List[dict]):
        """Initialize class.

        Args:
            data (str): Posts list
        """
        message = f"Failed to process data when requesting available posts;\nData: {data}"
        super().__init__(message)


class AllStationsOfflineError(Exception):
    """All stations offline."""

    def __init__(self):
        """Initialize class."""
        message = "Data could not be processed due to lack of online stations"
        super().__init__(message)


class GetMeasurementError(DataTransformationException):
    """Decoding error."""

    def __init__(self, data: List[dict]):
        """Initialize class.

        Args:
            data (str): Measurements
        """
        message = f"Data could not be processed when receiving the last measurement from the post;\nData: {data}"
        super().__init__(message)
