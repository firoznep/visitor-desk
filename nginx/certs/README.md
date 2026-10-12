Put your real certificate here as `fullchain.pem` and `privkey.pem` (e.g. from Let's Encrypt /
certbot, or your organisation's CA). Never commit real certificates or keys to version control.
For local testing only, generate a self-signed pair:

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout privkey.pem -out fullchain.pem -subj "/CN=localhost"
