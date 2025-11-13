# SSL setup

> [!WARNING]
> Domain name for your server is required.

Add domain name of your server to the `.env` file like this:

  ```text
  NGINX_SERVER_NAME=example.com
  ```

By default, an SSL certificate is issued by Let's Encrypt. It requires you to put your email to the `.env` file:

  ```text
  SSL_EMAIL=my@example.com
  ```

If you want to change Nginx port on host (443 by default), use `NGINX_HTTPS_PORT` environment variable in the `.env` file:

  ```text
  NGINX_HTTPS_PORT=8443
  ```

Run the app using Docker Compose:

  ```sh
  COMPOSE_PROFILES=https,acme docker compose -f docker-compose.yml up -d --build --remove-orphans

  # Or, if you also want to handle playlists
  COMPOSE_PROFILES=https,acme,with-pl docker compose -f docker-compose.yml up -d --build --remove-orphans
  ```

If you want to use your own SSL certificate files, add them to the `certs` directory and run Docker Compose without `acme` profile:

  ```sh
  COMPOSE_PROFILES=https docker compose -f docker-compose.yml up -d --build --remove-orphans

  # Or, if you also want to handle playlists
  COMPOSE_PROFILES=https,with-pl docker compose -f docker-compose.yml up -d --build --remove-orphans
  ```
