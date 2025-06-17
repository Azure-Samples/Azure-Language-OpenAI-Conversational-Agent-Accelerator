#!/bin/bash

set -e

echo "Authenticating to Azure..."
echo "Ensure you select the subscription you are deploying resources to..."

az login
azd auth login

echo "Authentication complete"
