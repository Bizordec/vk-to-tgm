FROM nginxinc/nginx-unprivileged:1.29.3-alpine3.22

ARG UID=1000
ARG GID=1000

COPY --chown=nginx:nginx ./default.conf.template /etc/nginx/templates/

USER nginx
