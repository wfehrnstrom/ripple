from pprint import pprint

verbose = True

def get_track_info(args):
    rb = args.rb
    td = args.td
    track_names = args.track_names

    for track_name in track_names:
        if verbose:
            print(f"Searching for {track_name}...")
        rb_track_result = rb.get_track_by_name(track_name)
        pprint(vars(rb_track_result))
        if verbose:
            print("Has tidal result?:")
            artist = rb.get_artist_by_id(rb_track_result.ArtistID)
            result = td.lookup_track(track_name, artist.Name)
            pprint(vars(result))

def get_track_info(args):
    rb = args.rb
    td = args.td
    track_names = args.track_names

    for track_name in track_names:
        if verbose:
            print(f"Searching for {track_name}...")
        rb_track_result = rb.get_track_by_name(track_name)
        pprint(vars(rb_track_result))
        if verbose:
            print("Has tidal result?:")
            artist = rb.get_artist_by_id(rb_track_result.ArtistID)
            result = td.lookup_track(track_name, artist.Name)
            pprint(vars(result)) 
        return rb_track_result

def get_agent_registry(_):
    cloud_agent_registry = rb.db.get_cloud_agent_registry().all()
    for agent in cloud_agent_registry:
        print(vars(agent))
