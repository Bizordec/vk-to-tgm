#!/bin/bash

function prompt_text {
    local prompt=$1
    local regex=$2
    local default=$3

    if [ -n "$default" ]; then
        prompt="$prompt [$default]"
    fi
    
    while true; do
        read -rp "-> $prompt: " ANSWER
        if echo "$ANSWER" | grep -qP "$regex"; then
            ret_val=$ANSWER
            break
        elif [ "$ANSWER" == "" ] && [ -n "$default" ]; then
            ret_val=$default
            break
        else
            echo Invalid input, try again...
        fi
    done
}

prompt_text "Enter installation path to delete" "^/.+$" "/srv/vk-to-tgm"
INSTALL_PATH=$ret_val

prompt_text "Enter app's owner" "^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$" "vtt-user"
VTT_USER=$ret_val

echo "Stopping services..."
sudo systemctl stop vtt-cb-receiver vtt-workers vtt-dbc-scheduler vtt-tgm-bot
sudo systemctl disable vtt-cb-receiver vtt-workers vtt-dbc-scheduler vtt-tgm-bot

echo "Deleting service configs..."
sudo rm -f "/etc/systemd/system/vtt-cb-receiver.service" \
    "/etc/systemd/system/vtt-workers.service" \
    "/etc/systemd/system/vtt-dbc-scheduler.service" \
    "/etc/systemd/system/vtt-tgm-bot.service" \
    "/etc/default/vtt-workers.conf"

sudo systemctl daemon-reload

echo "Deleting '$INSTALL_PATH'..."
sudo rm -rf "$INSTALL_PATH"

echo "Deleting user '$VTT_USER'..."
sudo userdel "$VTT_USER"

if [ -f /etc/nginx/sites-enabled/vtt-cb-receiver.conf ]; then
    echo "Deleting Nginx site config..."
    sudo rm /etc/nginx/sites-enabled/vtt-cb-receiver.conf
    sudo systemctl reload nginx
fi

echo "Uninstallation completed."
