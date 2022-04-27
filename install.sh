#!/bin/bash

prompt_yn() {
    local prompt=$1

    while true; do
    read -rp "-> $prompt [Y/n]: " yn
    case $yn in
        [yY][eE][sS]|[yY]|"") 
            ret_val=1
		    break
            ;;
        [nN][oO]|[nN]) 
            ret_val=0
            break
            ;;
        *) 
            echo Invalid input, try again...
    esac
    done
}

prompt_text() {
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

set_setting() {
    local file=$1
    local key=$2
    local value=$3
    local add_quotes=$4

    if [ "$add_quotes" == "y" ]; then
        value="\"$value\""
    fi
    
    if grep -q "$key=" "$file"; then
        # Escape sed characters.
        value=$(echo "$value" | sed 's/[\/&]/\\&/g')
        sudo sed -i "s/^\s*$key=.*/$key=$value/" "$file"
    else
        echo "$key=$value" | sudo tee -a "$file" 
    fi
}

main() {
    echo "Starting vk-to-tgm installation..."
    
    if ! command -v python3 &> /dev/null; then
        echo "Python3 not installed! Aborting."
        exit 1
    fi
    
    if ! command -v ffmpeg &> /dev/null; then
        echo "FFmpeg not installed! Aborting."
        exit 1
    fi

    prompt_yn "Do you want to setup Nginx server?"
    NGINX_ON=$ret_val
    if [ "$NGINX_ON" -eq 1 ]; then
        if ! command -v nginx &> /dev/null; then
            echo "Nginx is not installed! Aborting."
            exit 1
        fi
    fi

    prompt_text "Enter installation path" "^\/.*$" "/srv/vk-to-tgm"
    INSTALL_PATH=$ret_val

    prompt_text "Enter app's owner" "^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$" "vtt-user"
    VTT_USER=$ret_val

    if [ -f ".env" ]; then
        prompt_yn "Found .env file. Load it?"
        LOAD_ENV=$ret_val
        if [ "$LOAD_ENV" -eq 1 ]; then
            # Clean from comments and spaces and make all variables in single quotes.
            # shellcheck source=/dev/null
            if ! source <(sed -e '/^#/d;/^\s*$/d' -e "s/='\(.*\)'/=\1/g" -e "s/=\"\(.*\)\"/=\1/g" -e "s/=\(.*\)/='\1'/g" .env); then
                echo "Failed to load .env file."
                exit 1
            fi
        fi
    fi

    if [ -z "$VTT_LANGUAGE" ]; then
        prompt_text "Enter app's language (available: 'en', 'ru')" "^(en|ru)$" "en"
        VTT_LANGUAGE=$ret_val
    fi

    if [ -z "$TGM_CHANNEL_USERNAME" ] && [ -z "$TGM_CHANNEL_ID" ]; then
        prompt_yn "Is your main Telegram channel public?"
        IS_MAIN_PUBLIC=$ret_val
        if [[ "$IS_MAIN_PUBLIC" -eq 1 ]]; then
            prompt_text "Enter your main Telegram channel name" "^\w+$"
            TGM_CHANNEL_USERNAME=$ret_val
        else
            prompt_text "Enter your main Telegram channel id (starts with '-100')" "^-100\d+$"
            TGM_CHANNEL_ID=$ret_val
        fi
    fi

    if [ -z "$TGM_PL_CHANNEL_USERNAME" ] && [ -z "$TGM_PL_CHANNEL_ID" ]; then
        prompt_yn "Do you want to forward audio playlists (additional Telegram channel required)?"
        HAS_PL=$ret_val
        if [[ "$HAS_PL" -eq 1 ]]; then
            prompt_yn "Is your playlist Telegram channel public?"
            IS_PL_PUBLIC=$ret_val
            if [[ "$IS_PL_PUBLIC" -eq 1 ]]; then
                prompt_text "Enter your playlist Telegram channel name" "^\w+$"
                TGM_PL_CHANNEL_USERNAME=$ret_val
            else
                prompt_text "Enter your playlist Telegram channel id (starts with '-100')" "^-100\d+$"
                TGM_PL_CHANNEL_ID=$ret_val
            fi
        fi
    fi

    if [ -z "$SERVER_URL" ]; then
        prompt_text "Enter your server URL" "^https?:\/\/.+$"
        SERVER_URL=$ret_val
    fi

    if [ -z "$VK_COMMUNITY_ID" ]; then
        prompt_text "Enter your VK community id" "^[0-9]+$"
        VK_COMMUNITY_ID=$ret_val
    fi

    if [ -z "$VK_COMMUNITY_TOKEN" ]; then
        prompt_text "Enter your VK community token" "^.+$"
        VK_COMMUNITY_TOKEN=$ret_val
    fi

    if [ -z "$VK_SERVER_TITLE" ]; then
        prompt_text "Enter title for your VK Callback API server (1-14 characters)" "^.{1,14}$"
        VK_SERVER_TITLE=$ret_val
    fi

    if [ -z "$TGM_BOT_TOKEN" ]; then
        prompt_text "Enter your Telegram bot token" "^.+$"
        TGM_BOT_TOKEN=$ret_val
    fi

    if [ -z "$TGM_API_ID" ]; then
        prompt_text "Enter your Telegram app id" "^[0-9]+$"
        TGM_API_ID=$ret_val
    fi

    if [ -z "$TGM_API_HASH" ]; then
        prompt_text "Enter your Telegram app hash" "^.+$"
        TGM_API_HASH=$ret_val
    fi

    if [ -z "$TGM_CLIENT_PHONE" ]; then
        prompt_text "Enter your Telegram phone number" "^\+?[0-9]+$"
        TGM_CLIENT_PHONE=$ret_val
    fi

    if [ -z "$VK_LOGIN" ]; then
        prompt_text "Enter your VK login" "^.+$"
        VK_LOGIN=$ret_val
    fi

    if [ -z "$VK_PASSWORD" ]; then
        prompt_text "Enter your VK password" "^.+$"
        VK_PASSWORD=$ret_val
    fi

    echo "Setting up .env variables..."
    if [ ! -f ".env" ]; then
        sudo touch .env    
    fi
    set_setting ".env" "VTT_LANGUAGE" "$VTT_LANGUAGE" "y"
    set_setting ".env" "TGM_CHANNEL_USERNAME" "$TGM_CHANNEL_USERNAME" "y"
    set_setting ".env" "TGM_CHANNEL_ID" "$TGM_CHANNEL_ID" "y"
    set_setting ".env" "TGM_PL_CHANNEL_USERNAME" "$TGM_PL_CHANNEL_USERNAME" "y"
    set_setting ".env" "TGM_PL_CHANNEL_ID" "$TGM_PL_CHANNEL_ID" "y"
    set_setting ".env" "SERVER_URL" "$SERVER_URL" "y"
    set_setting ".env" "VK_COMMUNITY_ID" "$VK_COMMUNITY_ID" "y"
    set_setting ".env" "VK_COMMUNITY_TOKEN" "$VK_COMMUNITY_TOKEN" "y"
    set_setting ".env" "VK_SERVER_TITLE" "$VK_SERVER_TITLE" "y"
    set_setting ".env" "TGM_BOT_TOKEN" "$TGM_BOT_TOKEN" "y"
    set_setting ".env" "TGM_API_ID" "$TGM_API_ID" "y"
    set_setting ".env" "TGM_API_HASH" "$TGM_API_HASH" "y"
    set_setting ".env" "TGM_CLIENT_PHONE" "$TGM_CLIENT_PHONE" "y"
    set_setting ".env" "VK_LOGIN" "$VK_LOGIN" "y"
    set_setting ".env" "VK_PASSWORD" "$VK_PASSWORD" "y"

    echo "Setting up services config files..."
    sudo cp -f "app/celeryconfig.py.example" "app/celeryconfig.py" 
    
    sudo cp -f "setup/systemd/vtt-cb-receiver.service" "/etc/systemd/system/"
    set_setting "/etc/systemd/system/vtt-cb-receiver.service" "User" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-cb-receiver.service" "Group" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-cb-receiver.service" "WorkingDirectory" "$INSTALL_PATH"
    set_setting "/etc/systemd/system/vtt-cb-receiver.service" "Environment" "VTT_VENV=$INSTALL_PATH/.venv" "y"

    sudo cp -f "setup/systemd/vtt-workers.service" "/etc/systemd/system/" 
    set_setting "/etc/systemd/system/vtt-workers.service" "User" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-workers.service" "Group" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-workers.service" "WorkingDirectory" "$INSTALL_PATH"
    
    sudo cp -f "setup/systemd/vtt-dbc-scheduler.service" "/etc/systemd/system/" 
    set_setting "/etc/systemd/system/vtt-dbc-scheduler.service" "User" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-dbc-scheduler.service" "Group" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-dbc-scheduler.service" "WorkingDirectory" "$INSTALL_PATH"

    sudo cp -f "setup/systemd/vtt-tgm-bot.service" "/etc/systemd/system/" 
    set_setting "/etc/systemd/system/vtt-tgm-bot.service" "User" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-tgm-bot.service" "Group" "$VTT_USER"
    set_setting "/etc/systemd/system/vtt-tgm-bot.service" "WorkingDirectory" "$INSTALL_PATH"
    set_setting "/etc/systemd/system/vtt-tgm-bot.service" "Environment" "VTT_VENV=$INSTALL_PATH/.venv" "y"

    sudo cp -f "setup/configs/vtt-celery.conf" "/etc/default/"
    set_setting "/etc/default/vtt-celery.conf" "CELERY_BIN" "$INSTALL_PATH/.venv/bin/celery" "y"

    sudo systemctl daemon-reload

    if [ "$NGINX_ON" -eq 1 ]; then
        echo "Setting up Nginx config..."
        sudo cp -f "setup/nginx/vtt-cb-receiver.conf" "/etc/nginx/sites-available/"
        
        SERVER_NAME=$(echo "$SERVER_URL" | grep -Po 'https?://\K[^/]+')
        if ! grep -qx "\s*server_name\s*$SERVER_NAME;" "/etc/nginx/sites-available/vtt-cb-receiver.conf"; then
            sudo sed -i "/^\s*server {/a \ \ \ \ server_name $SERVER_NAME;" "/etc/nginx/sites-available/vtt-cb-receiver.conf"
        fi

        sudo ln -sf "/etc/nginx/sites-available/vtt-cb-receiver.conf" "/etc/nginx/sites-enabled/"
    fi

    echo "Creating user '$VTT_USER'..."
    if id -u "$VTT_USER" &> /dev/null; then
        echo "User '$VTT_USER' already exists."
    else
        sudo useradd -r "$VTT_USER"
        echo "User '$VTT_USER' created."
    fi

    echo "Installing in '$INSTALL_PATH'..."
    sudo mkdir -p "$INSTALL_PATH"
    if [ "$PWD" != "$(realpath -s "$INSTALL_PATH")" ]; then
        sudo cp -rf app/ locale/ .env requirements.txt uninstall.sh LICENSE README.md "$INSTALL_PATH"
        sudo mkdir -p "$INSTALL_PATH/logs"
    fi
    sudo chown -R "$VTT_USER": "$INSTALL_PATH"
    
    cd "$INSTALL_PATH" || exit 1

    sudo chmod o+w "$INSTALL_PATH"

    echo "Installing virtual environment..."
    sudo rm -rf .venv
    python3 -m venv .venv
    # shellcheck source=/dev/null
    source .venv/bin/activate
    python3 -m pip install wheel
    python3 -m pip install -r requirements.txt

    echo "Signing in VK and Telegram..."
    sudo chmod -f o+rw .env ./*.session &> /dev/null
    python3 -m app.sign_in
    sudo chmod o-rw .env ./*.session
    
    sudo chmod o-w "$INSTALL_PATH"
      
    sudo chown -R "$VTT_USER": "$INSTALL_PATH"

    echo "Starting services..."
    sudo systemctl restart vtt-cb-receiver vtt-workers vtt-dbc-scheduler vtt-tgm-bot
    sudo systemctl enable vtt-cb-receiver vtt-workers vtt-dbc-scheduler vtt-tgm-bot
    if [ "$NGINX_ON" -eq 1 ]; then
        sudo systemctl reload nginx
    fi

    echo "Installation completed."
}

main
