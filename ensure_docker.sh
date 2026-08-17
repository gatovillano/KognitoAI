#!/bin/bash
# Verify Docker service is running
systemctl is-active --quiet docker || exit 0
