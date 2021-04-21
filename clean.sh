#!/bin/sh
#
# run in addition to:
#
#  % python3 setup.py clean --all
#

echo '-- clean: removing build directories...'

rm -rf ./build ./dist ./*egg-info ./tests/__pycache__ ./.pytest_cache ./src/kros_core.egg-info

echo '-- clean: done.'
