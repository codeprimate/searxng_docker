#!/usr/bin/env sh
# Avoid broken global pytest plugins (e.g. jaxtyping) auto-loading on some hosts.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
exec python3 -m pytest "$@"
