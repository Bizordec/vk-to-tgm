#!/bin/sh

set -eo pipefail

if [ "$ENABLE_SSL" -eq 0 ]; then \
    echo "Skip SSL setup."
    exit 0
fi

echo "Setting up SSL..."
if [ -f /etc/nginx/ssl/key.pem ] && [ -f /etc/nginx/ssl/cert.pem ]; then
    echo "Using existing SSL certificates, removing redundant packages..."
    apk del openssl socat
    exit 0
fi

echo "Generating SSL certificates"
if [ -z "$NGINX_SERVER_NAME" ]; then
    echo "NGINX_SERVER_NAME is required."
    exit 1
fi
if [ -z "$SSL_EMAIL" ]; then
    echo "SSL_EMAIL is required"
    exit 1
fi

cd $HOME
curl https://get.acme.sh | sh -s email=$SSL_EMAIL

$HOME/.acme.sh/acme.sh --set-default-ca --server letsencrypt
$HOME/.acme.sh/acme.sh --issue -d "$NGINX_SERVER_NAME" --standalone --httpport 8080
$HOME/.acme.sh/acme.sh --install-cert -d "$NGINX_SERVER_NAME" \
    --key-file /etc/nginx/ssl/key.pem \
    --fullchain-file /etc/nginx/ssl/cert.pem
