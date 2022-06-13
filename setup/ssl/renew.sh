#!/bin/bash

openssl req -newkey rsa:2048 -sha256 -nodes -keyout vkapi.key -x509 -days 365 -out vkapi.crt -subj "/C=RU/ST=Saint Petersburg/L=Saint Petersburg/O=VK API Club/CN=vkapi"

openssl pkcs12 -export -in vkapi.crt -name "Test" -descert -inkey vkapi.key -out vkapi.p12 -passout pass:
