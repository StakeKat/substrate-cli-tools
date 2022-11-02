from subclient import setup_logging
from subtools.cli import Cli
from subtools import __app__
from subclient import get_endpoint_ids
import logging


# noinspection DuplicatedCode
def get_parser():
    import argparse
    parser = argparse.ArgumentParser(prog=__app__)
    parser.add_argument("chain", choices=get_endpoint_ids(), help="chain to use")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--cache-path", help="cache path", default="/tmp/cache")
    parser.add_argument("--no-cache", action="store_true", help="disable cache entirely")
    actions = parser.add_subparsers(help='action', dest='action', required=True)
    # Block dumper
    block = actions.add_parser('block', help='dump block or round info as json')
    block.add_argument('--block', '-b', help='start block to watch, default last', type=int, default=0)
    # Event watcher
    watch = actions.add_parser('event-watch', help='watch a single address for changes')
    watch.add_argument('--address', '-a', help='filter by name or address regexp')
    watch.add_argument('--method', '-e', help='filter method name or id with a regular expression', default=None)
    watch.add_argument('--min-amount', '-m', type=int, help='filter events with an amount lower')
    watch.add_argument('--tail', '-f', action="store_true", help="poll and keep watching for events")
    watch.add_argument('--count', '-c', type=int, help='how many blocks to look back', default=300)
    watch.add_argument('--format', help='output format', default='text', choices=['text', 'json'])
    # Done
    return parser.parse_args()


if __name__ == "__main__":
    args = vars(get_parser())
    setup_logging(__app__, logging.DEBUG if args.pop('debug') else logging.INFO)
    cli = Cli(
        chain=args.pop('chain'),
        cache_path=None if args.pop('no_cache') else args.pop('cache_path')
    )
    getattr(cli, args.pop('action').replace("-", "_"))(**args)
