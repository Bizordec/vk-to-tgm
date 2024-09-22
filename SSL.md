# SSL setup

> [!WARNING]
> Domain name for your server is required.

Add domain name of your server to the `.env` file like this:

  ```text
  NGINX_SERVER_NAME=example.com
  ```

By default, SSL certificate from Let's Encrypt is generated. It requires you to put your email to the `.env` file:

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

[If you want to add client SSL certificate, read this section](#add-client-ssl-certificate).

Run the app using Docker Compose:

  ```sh
  docker compose -f docker-compose.yml -f docker-compose.ssl.yml up --build --remove-orphans

  # Or, if you also want to handle playlists
  docker compose -f docker-compose.yml -f docker-compose.ssl.yml --profile with-pl up --build --remove-orphans
  ```

## Add client SSL certificate

1. Add to your `.env` file this line:

    ```text
    ENABLE_CLIENT_SSL=1
    ```

2. Create client SSL certificate (will work for 365 days):

    ```sh
    ./nginx/ssl/renew.sh
    ```

3. Go to your VK community page, `"Manage" > "Settings" > "API usage" > "Callback API" > "Server settings"`;
4. Select server with the name same as in the `VK_SERVER_TITLE` env variable (by default it's `vk-to-tgm`). If there is no such server, create one or edit name of the existing server.
5. Upload `vkapi.p12` file in the `SSL certificate` field.
