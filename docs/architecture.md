# Architecture

MAXBRIDGE is split into stable core layers plus an explicit experimental MAX boundary.

Stable core:

1. `config`: file and env driven runtime configuration.
2. `core`: typed models, client abstraction, sessions, and abstract transport interfaces.
3. `storage` and `archive`: durable local state, migrations, exports, and replay support.
4. `bridge` and `telegram`: routing, dedupe, forum-topic mapping, and owner-only control plane.
5. `cli`, `examples`, and `tests`: DX layer and operational tooling.

Experimental boundary:

1. `experimental`: mock MAX transport and future pluggable adapters.
2. `auth`: MAX login state and explicit placeholders for future safe local auth adapters.

The project intentionally keeps MAX-specific transport and auth out of the stable core by isolating them behind experimental adapters.
