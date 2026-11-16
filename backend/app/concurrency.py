from __future__ import annotations

import threading


# Held for the whole duration of an apply cycle. Enable/disable switches try to
# take it non-blocking and are rejected while an apply is running, so a batch
# can never be half-written under a conflicting enable/disable state.
apply_gate = threading.Lock()

# Serialises enable/disable switches among themselves (DB transactions already
# serialise them, this just avoids needless lock contention).
sku_write_gate = threading.Lock()
