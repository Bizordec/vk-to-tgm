#!/bin/sh

set -e

if [ "$ENABLE_SSL" -ne 0 ]; then
    mv /etc/nginx/ssl/default-ssl.conf.template /etc/nginx/templates/default.conf.template
fi
