FROM nginxinc/nginx-unprivileged:1.27.1-alpine3.20

ARG UID=1000
ARG GID=1000

ENV ENABLE_SSL=0
ENV ENABLE_CLIENT_SSL=0
ENV SSL_EMAIL=""
ENV NGINX_SERVER_NAME=""

USER root

# Install tools for ssl setup
RUN apk add --no-cache openssl socat

# The prefix is "0-"
# to make it run before entrypoint scripts of the nginx image
COPY ./0-change-default-conf.sh /docker-entrypoint.d/
# The prefix is "40-"
# to make it run after entrypoint scripts of the nginx image
COPY ./40-ssl-setup.sh /docker-entrypoint.d/

COPY --chown=nginx:nginx ./ssl/client-ssl.conf /etc/nginx/ssl/
COPY --chown=nginx:nginx ./ssl/default-ssl.conf.template /etc/nginx/ssl/
COPY --chown=nginx:nginx ./default.conf.template /etc/nginx/templates/

USER nginx
