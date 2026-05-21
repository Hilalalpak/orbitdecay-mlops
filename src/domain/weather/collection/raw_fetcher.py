import requests


class RawFetcher:

    @staticmethod
    def fetch(url: str, timeout: int) -> str:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
