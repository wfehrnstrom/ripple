import argparse
import logging
import warnings

from ripple.gateways import rekordbox_gateway, tidal_gateway
from ripple.utils.tidal_utils import analyze_tidal_tracks, refresh_single_track
from ripple.utils.rb_utils import get_track_info, get_agent_registry

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configure logging to save to a file
logging.basicConfig(
    filename='app.log',      # Name of the file where logs will be stored
    filemode='w',            # 'w' to overwrite each time, 'a' to append (default)
    level=logging.WARN,      # Minimum log level to capture
    format='%(asctime)s - %(levelname)s - %(message)s', # Log message format
    encoding='utf-8'         # Added in Python 3.9+ to handle special characters properly
)

def analyze_tidal_tracks_entrypoint(args):
    return analyze_tidal_tracks(args.rb, args.td)

def refresh_track_entrypoint(args):
    return refresh_single_track(args.track_name, args.artist_name, args.rb, args.td)


def main():
    print("Initialized rekordbox and tidal interfaces.")
    rb = rekordbox_gateway.RekordboxGateway()
    td = tidal_gateway.TidalGateway()

    parser = argparse.ArgumentParser("Utility for managing your rekordbox collection.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available subcommands")
    tidal_analysis_parser = subparsers.add_parser("analyze-tidal-tracks", help="Analyzes all tidal tracks in your rekordbox collection.")
    tidal_analysis_parser.set_defaults(func=analyze_tidal_tracks_entrypoint, rb=rb, td=td)

    refresh_track_parser = subparsers.add_parser("refresh-track", help="Reset analysis on a rekordbox track.")
    refresh_track_parser.add_argument("track_name", help="The name of the track in your rekordbox collection you want to refresh")
    refresh_track_parser.add_argument("artist_name", help="The name of the lead artist for the track you're refreshing")
    refresh_track_parser.set_defaults(func=refresh_track_entrypoint, rb=rb, td=td)

    get_track_info_parser = subparsers.add_parser("get-track-info", help="Get Rekordbox db info for tracks")
    get_agent_registry_parser = subparsers.add_parser("get-agent-registry", help="Get Rekordbox agents in DB registry.")

    get_track_info_parser.set_defaults(func=get_track_info, rb=rb, td=td)
    get_agent_registry_parser.set_defaults(func=get_agent_registry, r=rb, td=td)

    get_track_info_parser.add_argument("track_names", nargs="+", type=str, help="One or more names of rekordbox tracks in quotes.")

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()