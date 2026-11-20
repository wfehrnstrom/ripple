from __future__ import annotations

import json
import logging
import tidal
import concurrent
from datetime import datetime, timedelta
import time
import requests
import pathlib

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Callable,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
    no_type_check,
)

from pathlib import Path
from pprint import pprint

from tidal.configuration import Configuration
from tidal.api_client import ApiClient
from tidal.api.tracks_api import TracksApi
from tidal.api.search_results_api import SearchResultsApi

from ripple.gateways.exceptions import TooManyRequests

log = logging.getLogger(__name__)

class TidalGateway:
    credentials_path = Path("secrets/client_credentials.json")
    cached_token_path = Path("secrets/token.json")
    backoff_time_secs = 0.1
    client_id = None
    client_secret = None
    # ISO 3166 A2 style country code hardcoded for now
    country_code = "US"

    def client_credentials(self, path=credentials_path) -> Tuple[str, str]:
        """The client_id and client_secret for the limited input device login."""
        if not self.client_id and not self.client_secret:
            try:
                with path.open("r") as credentials_file:
                    data = json.load(credentials_file)
                    self.client_id = data["client_id"]
                    self.client_secret = data["client_secret"]
            except Exception as e:
                log.info("Could not load session from %s: %s", self.credentials_path, e)
            
        return self.client_id, self.client_secret

    # attempt to load tidal credentials from local token file.
    # If this fails, get a fresh token
    def _auth(self):
        self._client_credentials_auth()

    def get_cached_token(self):
        if not self.cached_token_path.exists():
            return None
        
        with open(self.cached_token_path) as token_file:
            return json.load(token_file)

    def _client_credentials_auth(self):
        token = None
        if self.token_expired():
            token = self.get_token()
            self.cache_token(token)

        if not token:
            token = self.get_cached_token()

        self.configuration = Configuration(access_token = token["access_token"])

    def get_token(self):
        url = "https://auth.tidal.com/v1/oauth2/token"
        client_id, client_secret = self.client_credentials()
        print(f"Client ID: {client_id}")

        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }

        response = requests.post(url, params)

        if not response.ok:
            log.error("Login failed: %s", response.text)
            response.raise_for_status()

        response_body = response.json()
        access_token = response_body['access_token']
        expiry_time = datetime.now() + timedelta(seconds=float(response_body['expires_in']))

        return {
            "access_token": access_token,
            "expiry_time": expiry_time.isoformat()
        }


    def cache_token(self, token):
        with open(self.cached_token_path, 'w+') as token_file:
            json.dump(token, token_file)
        
    def token_expired(self):
        if self.cached_token_path.exists():
            with open(self.cached_token_path) as token_file:
                token_json = json.loads(token_file.read())
                expiry_time = datetime.fromisoformat(token_json["expiry_time"])
                if datetime.now() < expiry_time:
                    return False
        return True

    def __init__(self):
        self._auth()
        self.api_client = ApiClient(self.configuration)
        self.tracks_api = TracksApi(self.api_client)
        self.search_results_api = SearchResultsApi(self.api_client)

    def lookup_ids(self, ids, backoff=True):
        return self.backoff_request(self.tracks_api.tracks_get, self.country_code, filter_id=ids) if backoff else self.tracks_api.tracks_get(self.country_code, filter_id=ids)

    def get_track_by_name_and_artist(self, track, artist):
        return self.search_results_api.search_results_get(self.country_code, filter_query=f"{track} {artist}", include=["tracks"])

    def lookup_track(self, track, artist, backoff=True):
        return self.backoff_request(self.session.get_track_by_name_and_artist, track, artist) if backoff else self.session.get_track_by_name_and_artist(track, artist)


    def lookup_track_with_info(self, track, artist, backoff=True):
        response = self.lookup_track(track, artist, backoff)
        if response:
            track_info_headline = f"------EXTENDED TIDAL INFORMATION: REPLACEMENT TRACK FOR \"{track}\" BY \"{artist}\"------------"
            print(track_info_headline)
            pprint(vars(response))
            print("".join(["-" for _ in range(len(track))]))

        return response


    def backoff_request(self, request, *args, **kw):
        response = None
        try:
            response = request(*args, **kw)
            self.backoff_time_secs = max(1, self.backoff_time_secs / 2)
        except TooManyRequests as e:
            log.error(e)
            time.sleep(self.backoff_time_secs)
            self.backoff_time_secs *= 2
        return response




        
