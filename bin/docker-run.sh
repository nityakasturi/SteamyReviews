docker run --env-file env --restart unless-stopped --name steamyreviews --detach --volume=/var/www/html/4300/SteamyReviews:/root/SteamyReviews -P steamyreviews:latest
