"""
Lightweight HTTP client wrapper for Space-Track API operations.
Handles authentication, session management, retries and request execution.
"""

import requests
from contextlib import contextmanager
from typing import Optional, List, Any, Dict, cast, Iterator, ContextManager
from requests.adapters import HTTPAdapter
from requests.sessions import Session
from urllib3.util.retry import Retry
from structlog.stdlib import BoundLogger

from src.shared.config.config_interfaces import PipelineConfigInterface




class SpaceTrackClient:
    """
    Robust API client for Space-Track with retry logic and structured logging.
    """

    def __init__(self,
                 pipeline_config: PipelineConfigInterface,
                 logger: BoundLogger) -> None:

        self.config = pipeline_config
        self.logger = logger

        self.use_test_server = self.config.use_space_track_test_server()
        self.base_url = self.config.get_space_track_base_url()
        self.username = self.config.get_space_track_username()
        self.password = self.config.get_space_track_password()

        self.max_retries = self.config.get_space_track_max_retries()
        self.timeout = self.config.get_space_track_session_timeout()
        self.batch_timeout_multiplier = self.config.get_batch_timeout_multiplier()

        # API paths from config
        self.auth_path = self.config.get_space_track_endpoint("auth_path")
        self.query_base = self.config.get_space_track_endpoint("query_base")

    # Session & Authentication
    def open_session(self) -> Session:
        """Opens a requests.Session with exponential backoff on 5xx/429."""
        session = requests.Session()
        retry_strategy = Retry(total=self.max_retries,
                               backoff_factor=0.5,
                               status_forcelist=[429, 500, 502, 503, 504],
                               allowed_methods=["HEAD", "GET", "POST"])

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        self.logger.debug("api_session_created",
                          retries=self.max_retries,
                          base_url=self.base_url)
        return session

    def authenticate(self, session: Session) -> bool:
        """Authenticates against Space-Track. Returns False on any failure."""
        login_url = f"{self.base_url}/{self.auth_path}"
        payload = {"identity": self.username, "password": self.password}

        try:
            resp = session.post(login_url, data=payload, timeout=self.timeout)
            if resp.status_code == 200:
                self.logger.info("api_login_success")
                return True

            self.logger.error("api_login_failed",
                              status_code=resp.status_code,
                              response=resp.text[:100]  )
            return False

        except requests.RequestException as e:
            self.logger.error("api_login_exception", error=str(e))
            return False

    #######################
    # Data Fetching Methods
    #######################
    def fetch_bulk_history_stream(self,
                                  session: Session,
                                  norad_ids: List[str]) -> ContextManager[Optional[requests.Response]]:
        """Streams bulk TLE history for the given NORAD IDs. Must be used as a context manager."""

        ids_str = ",".join(map(str, norad_ids))
        endpoint = self.config.get_space_track_endpoint("historical_data")

        # Query: Order by EPOCH ASC
        query_path = f"{endpoint}/NORAD_CAT_ID/{ids_str}/orderby/EPOCH%20ASC/format/json"

        # Bulk operations need more time
        extended_timeout = self.timeout * self.batch_timeout_multiplier

        return self._execute_query_stream(
            session=session,
            query_path=query_path,
            timeout=extended_timeout,
            context=f"batch_stream_{norad_ids[0]}")

    def fetch_updates_since(self,
                            session: Session,
                            norad_ids: List[str],
                            start_date: str) -> List[Dict]:

        ids_str = ','.join(map(str, norad_ids))
        endpoint = self.config.get_space_track_endpoint('historical_data')

        # Query: EPOCH > start_date
        query_path = f"{endpoint}/NORAD_CAT_ID/{ids_str}/EPOCH/>{start_date}/orderby/EPOCH%20ASC/format/json"

        extended_timeout = self.timeout * self.batch_timeout_multiplier

        return self._execute_query(
            session=session,
            query_path=query_path,
            timeout=extended_timeout,
            context=f"bulk_inc_fetch_{len(norad_ids)}_sats")

    def fetch_data_by_query(self,
                            session: Session,
                            query_path: str,
                            timeout: float) -> List[Any]:
        """Executes an arbitrary Space-Track query. Used for catalog-style ad-hoc requests."""
        return self._execute_query(session, query_path, timeout, context="generic_query")

    ###########################
    # Internal Execution Engine
    ###########################
    def _execute_query(self,
                       session: Session,
                       query_path: str,
                       timeout: float,
                       context: str) -> List[Any]:
        """Executes an arbitrary Space-Track query. Used for catalog-style requests."""

        url = f"{self.base_url}/{self.query_base}/{query_path}"
        self.logger.debug("api_request_start", context=context, url_fragment=query_path[:50])

        try:
            response = session.get(url, timeout=timeout)

            if response.status_code != 200:
                # 404 usually means no data found for criteria, which is a warning, not an error.
                log_method = self.logger.warning if response.status_code == 404 else self.logger.error
                log_method(
                    "api_request_failed",
                    context=context,
                    status_code=response.status_code,
                    reason=response.reason)
                return []

            data = response.json()
            self.logger.debug("api_response_received", context=context, records=len(data))
            return cast(List[Any], data)

        except requests.exceptions.Timeout:
            self.logger.error("api_timeout", context=context, timeout_setting=timeout)
            return []

        except Exception as e:
            self.logger.error("api_unexpected_error", context=context, error=str(e))
            return []

    @contextmanager
    def _execute_query_stream(self,
                              session: Session,
                              query_path: str,
                              timeout: float,
                              context: str) -> Iterator[Optional[requests.Response]]:
        """Streams a Space-Track query. Yields the raw response for ijson consumption."""

        url = f"{self.base_url}/{self.query_base}/{query_path}"
        self.logger.debug("api_stream_request_start", context=context, url_fragment=query_path[:50])

        try:
            with session.get(url, timeout=timeout, stream=True) as response:
                if response.status_code != 200:
                    self.logger.error(
                        "api_stream_failed",
                        context=context,
                        status=response.status_code,
                        reason=response.reason)
                    yield None
                else:
                    yield response

        except Exception as e:
            self.logger.error("api_stream_exception", context=context, error=str(e))
            yield None

