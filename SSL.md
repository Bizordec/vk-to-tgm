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

If you want to use your SSL certificate, mount your certificate files in the [docker-compose.ssl.yaml](./docker-compose.ssl.yml):

  ```yaml
  services:
    nginx:
      # ...
      volumes:
        # ...
        - /path/to/your/cert.pem:/etc/nginx/ssl/cert.pem;
        - /path/to/your/key.pem:/etc/nginx/ssl/key.pem;
  ```

Run the app using Docker Compose:

  ```sh
  docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d --build --remove-orphans

  # Or, if you also want to handle playlists
  docker compose -f docker-compose.yml -f docker-compose.ssl.yml --profile with-pl up -d --build --remove-orphans
  ```
