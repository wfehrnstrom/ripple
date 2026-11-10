import typing
import pyrekordbox as prbox

from sqlalchemy import inspect

from pyrekordbox.masterdb import models as rbmodels

class RekordboxGateway:
    """ 
        Convenience interface layer for common operations on rekordbox's database.

        Unless stated otherwise, assume that when id is referred to, 
        the rekordbox id of the associated object is meant.
    """
    def streaming_filename_col():
        return rbmodels.DjmdContent.FileNameL

    def streaming_foldername_col():
        return rbmodels.DjmdContent.FolderPath

    def isrc_col():
        return rbmodels.DjmdContent.ISRC

    def strip_streaming_prefix_from_id(full_id):
        return full_id[full_id.rfind(":") + 1:]

    def __init__(self):
        self.db = prbox.MasterDatabase()
        self.streaming_prefixes = {"tidal": "tidal:"}

    def __del__(self):
        self.db.close()

    # TODO: generalize this to any streaming service
    '''
     Returns a dictionary keyed on the tidal id of the rekordbox track, where each key points to the track representation in rekordbox.
    '''
    def get_tidal_tracks(self):
        # Query the rekordbox subtable "DjmdContent" for tidal tracks
        query = self.db.query(rbmodels.DjmdContent)
        # If the track is a tidal track, it's FileNameL field will be prefixed with tidal:{ID} where {ID} is
        # some opaque string that we extract and use to hit the tidal API
        tidal_prefix_query_condition = RekordboxGateway.streaming_filename_col().startswith(self.streaming_prefixes["tidal"])
        results = query.filter(tidal_prefix_query_condition).all()

        id_to_track = {}

        for result in results:
            tidal_id = RekordboxGateway.strip_streaming_prefix_from_id(
                getattr(result, RekordboxGateway.streaming_filename_col().key))
            id_to_track[tidal_id] = result

        return id_to_track

    def get_track_by_name(self, name):
            query = self.db.query(rbmodels.DjmdContent)
            return query.filter(rbmodels.DjmdContent.Title == name).one()

    # TODO: generalize this to any streaming service
    def get_tidal_id_of_track(self, title):
        # Query the rekordbox subtable "Content" for tidal tracks
        track = self.get_track_by_name(title)
        return RekordboxGateway.strip_streaming_prefix_from_id(
            getattr(track, RekordboxGateway.streaming_filename_col().key))

    def get_artist_by_id(self, id):
        # Query the rekordbox subtable "DjmdArtist"
        return self.db.get_artist(ID=id)

    def write_track(self, track: rbmodels.DjmdContent, attrs=None):
        # Example of writing track to rekordbox db: https://github.com/dylanljones/pyrekordbox/blob/master/pyrekordbox/masterdb/database.py#L1972
        # if no attributes to write specified, write all information about the track that can be mapped
        if track is not None:
            insp = inspect(track)
            if not insp.persistent and not insp.pending:
                track = self.db.session.merge(track)
                self.db.session.commit()
            else:
                print("Track changes are already persisted in the database. Skipping write operation.")
