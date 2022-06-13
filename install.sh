#!/bin/bash

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

    source functions.sh

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
    
    set_env

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
        setup_nginx
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
        sudo cp -rf app/ locale/ functions.sh .env requirements.txt uninstall.sh LICENSE README.md "$INSTALL_PATH"
        sudo mkdir -p "$INSTALL_PATH/logs"
    fi
    sudo chown -R "$VTT_USER": "$INSTALL_PATH"
    
    cd "$INSTALL_PATH" || exit 1

    sudo chmod o+w "$INSTALL_PATH"

    echo "Installing virtual environment..."
    sudo rm -rf .venv
    python3 -m venv .venv
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

    echo "Installation completed."
}

main
