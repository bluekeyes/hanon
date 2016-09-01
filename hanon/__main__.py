import sys

import mido

from hanon.cli import main, CliConfigError


# portmidi seems to have weird buffering problems
mido.set_backend('mido.backends.rtmidi')

try:
    code = main()
    sys.exit(code)
except KeyboardInterrupt:
    print()
    sys.exit(1)
except CliConfigError as err:
    print(str(err), file=sys.stderr)
    sys.exit(1)
