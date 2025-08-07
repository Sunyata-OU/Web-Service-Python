#!/bin/bash

# Legacy script - redirects to improved version
# This script is maintained for backward compatibility

echo "================================================================"
echo "NOTICE: This script has been replaced with an improved version."
echo "The new script is located at: scripts/init-ssl.sh"
echo "================================================================"
echo ""
echo "The new script provides:"
echo "  - Better error handling and validation"
echo "  - Staging environment testing"
echo "  - Domain extraction from .env file"
echo "  - Comprehensive logging"
echo "  - More configuration options"
echo ""
echo "Usage examples:"
echo "  ./scripts/init-ssl.sh --email user@example.com --domain example.com"
echo "  ./scripts/init-ssl.sh --help"
echo ""

read -p "Do you want to run the new improved script? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ $REPLY == "" ]]; then
    if [[ -f "scripts/init-ssl.sh" ]]; then
        echo "Running improved SSL setup script..."
        exec ./scripts/init-ssl.sh "$@"
    else
        echo "Error: New script not found at scripts/init-ssl.sh"
        exit 1
    fi
else
    echo "Proceeding with legacy script..."
    echo "Note: This legacy version may have issues and is not recommended."
fi

echo ""
echo "================================================================"
echo "LEGACY SCRIPT - NOT RECOMMENDED FOR PRODUCTION USE"
echo "================================================================"

if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

domains=(example.com)  # Changed from hardcoded domain
rsa_key_size=4096
data_path="./certbot"
email="" # Adding a valid address is strongly recommended
staging=0 # Set to 1 if you're testing your setup to avoid hitting request limits

echo "WARNING: Please update the 'domains' array in this script with your actual domain"
echo "Current domains: ${domains[@]}"
read -p "Continue anyway? (y/N) " decision
if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
  exit
fi

if [ -d "$data_path" ]; then
  read -p "Existing data found for $domains. Continue and replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi


if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "### Creating dummy certificate for $domains ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker-compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo


echo "### Starting nginx ..."
docker-compose --profile nginx up --force-recreate -d nginx
echo

echo "### Deleting dummy certificate for $domains ..."
docker-compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot
echo


echo "### Requesting Let's Encrypt certificate for $domains ..."
#Join $domains to -d args
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

# Enable staging mode if needed
if [ $staging != "0" ]; then staging_arg="--staging"; fi

docker-compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot
echo

echo "### Reloading nginx ..."
docker-compose exec nginx nginx -s reload
