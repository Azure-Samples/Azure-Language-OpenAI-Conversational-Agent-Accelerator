#!/bin/bash

set -ex

git fetch
git pull

azd init
