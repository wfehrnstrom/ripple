import itertools

from pprint import pprint
from tqdm import tqdm

from ripple.models.track import Track

MAX_TIDAL_API_RESULT_AMT = 20
PPRINT_CHAR_LIM = 120
verbose = True


def pprint_msg(msg, header_msg = None):
    div = ""
    footer_div = ""
    if header_msg:
        div = ['-' for _ in range(len(msg) + len(header_msg) + 2)]
        midpoint = len(div) // 2
        div[midpoint - (len(header_msg) // 2) - 1: midpoint + (len(header_msg) // 2) + 1] = f" {header_msg} "
        div = "".join(div)
        footer_div = "".join(['-' for _ in range(min(len(msg), PPRINT_CHAR_LIM))])
    else:
        footer_div = div = "".join(['-' for _ in range(min(len(msg), PPRINT_CHAR_LIM))])

    print(div)
    pprint(msg)
    print(footer_div)


def pprint_obj(o, header_msg = None):
    pprint_msg(vars(o), header_msg)


def paginate_list(l, pagination_amt=MAX_TIDAL_API_RESULT_AMT):
    return [l[i:min(i+pagination_amt, len(l))] for i in range(0, len(l), pagination_amt)]


def add_all_optional_results_from(fn, *args):
    result = fn(*args)
    if result is None:
        result = []
        if verbose:
            print(f"Didn't get a response back for {fn.__name__}({', '.join(map(str, args))})")
    return result


def check_tidal_catalogue_for_freshness(td, paginated_track_tidal_ids):
    
    id_to_result = {}

    msg = "Checking for stale tidal tracks in the local rekordbox database"
    for tidal_track_ids in tqdm(paginated_track_tidal_ids, msg):
        # TODO: Probably some way to get all needed track information to replace stale tracks in one go.
        #  Right now, a track is considered stale if it doesn't have a current entry in tidal's catalogue for the tidal # ID it currently has.
        result_tracks = td.lookup_ids(tidal_track_ids)
        if result_tracks is not None:
            id_to_result.update({str(track.id): track for track in result_tracks})
        elif verbose and result_tracks is None:
            print(f"Didn't get a response back for tidal track ids: {", ".join(tidal_track_ids)}")

    return id_to_result


def analyze_tidal_tracks(rb, td):
    if verbose:
        print("Beginning Stale tidal track cleanup...")

    # Get all tidal track ids, paginated to the maximum amount of filter IDs the TIDAL API will accept
    tidal_id_to_track = rb.get_tidal_tracks()
    paginated_track_tidal_ids = paginate_list(list(tidal_id_to_track.keys()))
    original_tidal_ids = set(tidal_id_to_track.keys())

    tidal_id_to_catalogue_result = check_tidal_catalogue_for_freshness(td, paginated_track_tidal_ids)

    # The stale IDs are the ones that were requested but we didn't get a response back for.
    stale_tidal_ids = original_tidal_ids - set(tidal_id_to_catalogue_result.keys())
    print(f"Found {len(stale_tidal_ids)} stale IDs out of {len(tidal_id_to_track)} total IDs")

    found_replacement_count = 0
    msg = "Replacing all stale tidal tracks."
    for stale_tidal_id in tqdm(stale_tidal_ids, msg):
        stale_track = tidal_id_to_track[stale_tidal_id]
        track_name = stale_track.Title
        print(f"\t- {track_name}")

        artist = rb.get_artist_by_id(stale_track.ArtistID)
        if artist is None:
            if verbose:
                print(f"Skipping finding a replacement track for {track_name} because it isn't associated with any artist in Rekordbox. Please fixup track and try again.")
            continue

        artist_name = artist.Name
        # TODO: Implement some fuzzy match algorithm to ensure that the replacement track isn't actually just some random track. Right now it only matches a replacement track on an exact match, which is too strict.
        replacement_track = td.lookup_track_with_info(track_name, artist_name)
        if not replacement_track:
            if verbose:
                print(f"Couldn't find a replacement track on TIDAL for {track_name} by {artist_name}")
            continue

        found_replacement_count += 1

        if verbose:
            print(f"Old Track {(stale_tidal_id, track_name, artist_name)} -> {(str(replacement_track.id), replacement_track.name, replacement_track.artist.name)}")

        intermediate_replacement_track_repr = Track.from_tidal_track(replacement_track)
        intermediate_replacement_track_repr.bind(stale_track.ID)
        rekordbox_track_repr = intermediate_replacement_track_repr.to_rb_track()

        # Change the tidal_id_to_track mapping to a tuple to signal we've found a replacement track
        tidal_id_to_track[stale_tidal_id] = (stale_track, rekordbox_track_repr)

        print("--------------COMPARISON BETWEEN OLD AND NEW REKORDBOX TRACK---------------------")
        pprint_obj(stale_track, "STALE TRACK")
        pprint_obj(rekordbox_track_repr, "NEW TRACK")

        if rekordbox_track_repr is not None:
            conf = input(f"Confirm track replacement:\r\nOld Track {(stale_tidal_id, track_name, artist_name)} -> New Track {(str(replacement_track.id), replacement_track.name, replacement_track.artist.name)} to rekordbox database? (y/n/stop): ")
            if conf.lower() == "y":
                print(f"Writing replacement track {replacement_track.name} with tidal ID {str(replacement_track.id)} and RB ID {rekordbox_track_repr.ID} to rekordbox database...")
                rb.write_track(rekordbox_track_repr)
            elif conf.lower() == "stop":
                print("User requested stop to replacement. Aborting.")
                break
            else:
                print("Skipping writing a replacement track for {track_name}.")

            
    print(f"Found replacements for {found_replacement_count}/{len(stale_tidal_ids)} stale tidal tracks.")


def refresh_single_track(track_name, artist_name, rb, td):
    print(f"Refreshing/Clearing analysis fields for track \"{track_name}\" by \"{artist_name}\"")
    replacement_track = td.lookup_track_with_info(track_name, artist_name)
    rb_track = rb.get_track_by_name(track_name)
    old_artist_name = rb.get_artist_by_id(rb_track.ArtistID).Name

    if not rb_track:
        print(f"This tool is only for refreshing tracks that already exist in your rekordbox database - Couldn't find track named \"{track_name}\" by \"{artist_name}\"")
        return
    
    intermediate_replacement_track_repr = Track.from_tidal_track(replacement_track)
    intermediate_replacement_track_repr.bind(rb_track.ID)
    rekordbox_track_repr = intermediate_replacement_track_repr.to_rb_track()

    print("--------------COMPARISON BETWEEN OLD AND NEW REKORDBOX TRACK---------------------")
    pprint_obj(rb_track, "STALE TRACK")
    pprint_obj(rekordbox_track_repr, "NEW TRACK")

    if rekordbox_track_repr is not None:
        conf = input(f"Confirm track refresh for {(rb_track.ID, rb_track.Title, old_artist_name)} -> New Track {(str(rekordbox_track_repr.ID), intermediate_replacement_track_repr.title, intermediate_replacement_track_repr.artist.name)} to rekordbox database? (y/n): ")
        if conf.lower() == "y":
            print(f"Writing replacement track {replacement_track} with tidal ID {str(intermediate_replacement_track_repr.streaming_id)} and RB ID {rekordbox_track_repr.ID} to rekordbox database...")
            rb.write_track(rekordbox_track_repr)
        else:
            print(f"Skipping writing a replacement track for {track_name}.")
        

        
