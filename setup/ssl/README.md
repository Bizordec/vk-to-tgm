# Client SSL certificate setup

1. Setup server SSL certificate. [Certbot](https://certbot.eff.org/) can help you with that;
2. Create client self-signed certificate (will work for 365 days):

    ```bash
    openssl req -newkey rsa:2048 -sha256 -nodes -keyout vkapi.key -x509 -days 365 -out vkapi.crt -subj "/C=RU/ST=Saint Petersburg/L=Saint Petersburg/O=VK API Club/CN=vkapi"

    openssl pkcs12 -export -in vkapi.crt -name "Test" -descert -inkey vkapi.key -out vkapi.p12 -passout pass:
    ```

3. Go to your VK community page, `"Manage" > "Settings" > "API usage" > "Callback API" > "Server settings"` and upload `vkapi.p12` file;
4. Add following lines to the nginx config:

    ```nginx
    ssl_client_certificate </path/to/vkapi.crt>;
    ssl_verify_client on;
    ssl_verify_depth 0;
    ```

5. Restart nginx:

    ```bash
    sudo service nginx restart
    ```
