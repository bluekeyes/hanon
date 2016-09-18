import sys

import mido
import mido.backends.rtmidi

from hanon import cli

def main():
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
