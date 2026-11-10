import pickle

from datetime import time
from hashlib import shake_128
from typing import Optional
from pyrekordbox.masterdb.models import DjmdContent as RbTrack

from ripple.models.artist import Artist
from ripple.models.streaming_service import StreamingService
from ripple.gateways.rekordbox_gateway import RekordboxGateway

class DbBindingError(Exception):
    def __init__(self, message):
        self.message = message

class Track:
    # unique ID for the track as maintained in the ripple database.
    id: str
    schema_version: str = "1.0.0"
    # A dictionary that maps between streaming service IDs and the track's unique ID for that
    # streaming service.
    streaming_ids: Optional[dict]
    streaming_urls: Optional[dict]
    title: str
    duration: int
    artist: Artist
    filepath: Optional[str]
    filename: Optional[str]
    explicit: bool = False
    last_modified_time: time
    imported_to_collection_time: time
    rb_id: Optional[str]
    rb_artist_id: Optional[str]
    rb_album_id: Optional[str]
    rb_hot_cue_ids: Optional[set[str]]
    rb_mem_cue_ids: Optional[set[str]]
    streaming_url: Optional[str]
    streaming_service: Optional[StreamingService]
    streaming_id: Optional[str]
    user_tags: Optional[set]
    user_attributes: Optional[dict]
    bitrate_kbps: int
    bpm: int
    key: Optional[str]
    isrc: Optional[str]

    @staticmethod
    def _get_streaming_filename_for_track(streaming_service, streaming_id):
        # TODO: If we end up supporting more streaming platforms, we will need to change the format of filenameL depending on the streaming service.
        if streaming_service is not None and streaming_id is not None:
            return f"{streaming_service.value}:tracks:{streaming_id}"

    @staticmethod
    def from_tidal_track(tidal_track):
        t = Track()

        # Set Streaming/Provenance related attributes
        t.streaming_url = tidal_track.url
        t.streaming_service = StreamingService.TIDAL
        t.streaming_urls = {t.streaming_service: t.streaming_url}
        t.streaming_id = tidal_track.id
        t.filename = Track._get_streaming_filename_for_track(t.streaming_service, t.streaming_id)

        # Core attributes describing the track itself.
        t.title = tidal_track.title
        t.bpm = tidal_track.bpm
        t.key = tidal_track.key
        t.isrc = tidal_track.isrc
        t.artist = Artist(tidal_track.artist.name)
        t.duration = tidal_track.duration
        t.explicit = tidal_track.explicit

        t.id = t.get_hash_id()

        return t
    
    '''
        The hash ID of a track is based on a few select attributes that are meant to prove song equality. If two hashes of a song are equal, they should be considered equivalent tracks by ripple.
    '''
    def get_hash_id(self):
        # TODO: base ID generation on attributes of the track that are inherent to audio and essential identifiers like the name.
        #  This way, in the future when users might have multiple different duplicates of a track on
        # different streaming platforms, but that essentially are the same song (same bpm, same key, same length, same audio data), we group them together.
        hash_input = pickle.dumps(f"{self.title}{self.artist}{self.duration}{self.bpm}{self.key}{self.isrc}")
        hash = shake_128(hash_input, usedforsecurity=False)
        return hash.hexdigest(10)
    
    '''
    
    Binds a track to a mixing software. All that binding does in a concrete sense is create/provide the data necessary
    for a track to be recognized by a mixing platform like rekordbox.
    
    '''
    def bind(self, rb_id):
        self.rb_id = rb_id

    def get_streaming_filename(self):
        return Track._get_streaming_filename_for_track(self.streaming_service, self.streaming_id)

    def to_rb_track(self, **kwargs):
        if not self.rb_id:
            raise DbBindingError("Track must be bound to the RB db with bind(ID) before converting to a rekordbox representation.")
        
        # IDs required for joining to records within the RB database.
        rb_track = RbTrack(**kwargs)
        # TBD whether these fields are truly redundant, or if they affect different parts of RB DB linkages.
        rb_track.ID = self.rb_id
        rb_track.MasterSongID = self.rb_id
        # Magic codes pulled from inspecting the SQL state of a forced failed load of a tidal track into rekordbox.
        # The purpose of these fields as a collection is to force rekordbox to reload the tidal audio file and re-analyze the track.
        rb_track.ContentLink = 14
        rb_track.Analysed = 0
        rb_track.AnalysisUpdated = None
        rb_track.AnalysisDataPath = ""
        rb_track.ExtInfo = 'null'
        rb_track.rb_data_status = 0
        rb_track.rb_local_data_status = 0

        streaming_filename = self.get_streaming_filename()
        if streaming_filename:
            # Rekordbox internally sets the filename and folderpath the same for streaming tracks. Since I don't know if this is the case for other streaming services, I'm defensively just triggering this behavior on tidal streamed tracks.
            # TODO: Confirm if this is the case for other streaming services
            if self.streaming_service == StreamingService.TIDAL:
                setattr(rb_track, RekordboxGateway.streaming_filename_col().key, streaming_filename)
                setattr(rb_track, RekordboxGateway.streaming_foldername_col().key, streaming_filename)
        if self.isrc:
            setattr(rb_track, RekordboxGateway.isrc_col().key, self.isrc)
        return rb_track


