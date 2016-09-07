import sys

import mido

from hanon import cli

def main():
    # portmidi seems to have weird buffering problems
    mido.set_backend('mido.backends.rtmidi')
    try:
        code = cli.main()
        sys.exit(code)
    except KeyboardInterrupt:
        print()
        sys.exit(1)
    except cli.ConfigError as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)
