import asyncio
import sys

if len(sys.argv) == 3 and sys.argv[1] == "pair":
    from .cli import pair

    sys.exit(asyncio.run(pair(sys.argv[2])))

from .app import main

main()
