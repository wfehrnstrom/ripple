import logging
import tidalapi
import time

from pathlib import Path
from pprint import pprint

from tidalapi.exceptions import TooManyRequests

logger = logging.getLogger(__name__)

class TidalGateway:
    credentials_path = Path("secrets/tidal-credentials.json")
    backoff_time_secs = 0.1

    # attempt to load tidal credentials from local token file.
    # If this fails or if the credentials need to be refreshed, print out a browser authentication link on Console
    def _auth(self):
        self.credentials_path.touch()

        try:
            session_loaded = self.session.load_session_from_file(self.credentials_path)

            if not session_loaded:
                self.session.login_oauth_simple(fn_print=print)

                if self.session.check_login():
                    self.session.save_session_to_file(self.credentials_path)
        except:
            self.session.login_oauth_simple(fn_print=print)

            if self.session.check_login():
                self.session.save_session_to_file(self.credentials_path)


    def __init__(self):
        self.session = tidalapi.Session()
        self._auth()


    def lookup_ids(self, ids, backoff=True):
        return self.backoff_request(self.session.get_tracks_by_id, ids) if backoff else self.session.get_tracks_by_id(ids)


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


    def backoff_request(self, request, *args):
        response = None
        try:
            response = request(*args)
            self.backoff_time_secs = max(1, self.backoff_time_secs / 2)
        except TooManyRequests as e:
            logger.error(e)
            time.sleep(self.backoff_time_secs)
            self.backoff_time_secs *= 2
        return response




        
