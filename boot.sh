# Create and activate virtual Env
sudo apt-get update
sudo apt install -y postgresql
sudo apt install -y redis
/opt/bitnami/python/bin/python3.11 -m venv /home/bitnami/.venv

# Placeholder for vars.
touch /home/bitnami/.env

# Create git dir
mkdir /home/bitnami/relentropygetter.git
mkdir /home/bitnami/relentropygetter
cd /home/bitnami/relentropygetter.git
git config --global init.defaultBranch main
git init --bare
cd /home/bitnami

# Create post receive
touch /home/bitnami/relentropygetter.git/hooks/post-receive
cat > /home/bitnami/relentropygetter.git/hooks/post-receive <<- "EOF"
#!/bin/bash
cd ~
git --work-tree="relentropygetter" --git-dir="relentropygetter.git" checkout -f main
source .venv/bin/activate
cd relentropygetter
pip install -r requirements.txt
deactivate
sudo /opt/bitnami/ctlscript.sh restart apache
sudo systemctl stop celeryd
sudo systemctl daemon-reload
sudo systemctl enable celeryd
sudo systemctl start celeryd
EOF
chmod +x /home/bitnami/relentropygetter.git/hooks/post-receive

# Apache Server
touch /opt/bitnami/apache/conf/vhosts/relentropygetter-http-vhost.conf
cat > /opt/bitnami/apache/conf/vhosts/relentropygetter-http-vhost.conf <<- "EOF"
<IfDefine !IS_relentropygetter_LOADED>
    Define IS_relentropygetter_LOADED
    WSGIDaemonProcess relentropygetter python-home=/home/bitnami/.venv python-path=/home/bitnami/relentropygetter
</IfDefine>
<VirtualHost 127.0.0.1:80 _default_:80>
ServerAlias *
WSGIProcessGroup relentropygetter
WSGIScriptAlias / /home/bitnami/relentropygetter/relentropygetter/wsgi.py
<Directory /home/bitnami/relentropygetter/relentropygetter>
    <Files wsgi.py>
    Require all granted
    </Files>
</Directory>
</VirtualHost>
EOF

touch /opt/bitnami/apache/conf/vhosts/relentropygetter-https-vhost.conf
cat > /opt/bitnami/apache/conf/vhosts/relentropygetter-https-vhost.conf <<- "EOF"
<IfDefine !IS_relentropygetter_LOADED>
    Define IS_relentropygetter_LOADED
    WSGIDaemonProcess relentropygetter python-home=/home/bitnami/.venv python-path=/home/bitnami/relentropygetter
</IfDefine>
<VirtualHost 127.0.0.1:443 _default_:443>
ServerAlias *
SSLEngine on
SSLCertificateFile "/opt/bitnami/apache/conf/bitnami/certs/server.crt"
SSLCertificateKeyFile "/opt/bitnami/apache/conf/bitnami/certs/server.key"
WSGIProcessGroup relentropygetter
WSGIScriptAlias / /home/bitnami/relentropygetter/relentropygetter/wsgi.py
<Directory /home/bitnami/relentropygetter/relentropygetter>
    <Files wsgi.py>
    Require all granted
    </Files>
</Directory>
</VirtualHost>
EOF

sudo chown -R bitnami /home/bitnami/.venv
sudo chown -R bitnami /home/bitnami/relentropygetter
sudo chown -R bitnami /home/bitnami/relentropygetter.git

touch /etc/systemd/system/celeryd.service
cat > /etc/systemd/system/celeryd.service <<- "EOF"
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=bitnami
Group=bitnami
EnvironmentFile=/home/bitnami/.env
EnvironmentFile=/etc/default/celeryd
WorkingDirectory=/home/bitnami/relentropygetter
ExecStart=/bin/sh -c '${CELERY_BIN} multi start ${CELERYD_NODES} -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'
ExecStop=/bin/sh -c '${CELERY_BIN} multi stopwait ${CELERYD_NODES} --pidfile=${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c '${CELERY_BIN} multi restart ${CELERYD_NODES} -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

touch /etc/default/celeryd
cat > /etc/default/celeryd <<- "EOF"
# The names of the workers. This example create one worker
CELERYD_NODES="worker1"

# The name of the Celery App, should be the same as the python file
# where the Celery tasks are defined
CELERY_APP="relentropygetter"

# Log and PID directories
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_PID_FILE="/var/run/celery/%n.pid"

# Log level
CELERYD_LOG_LEVEL=INFO

# Path to celery binary, that is in your virtual environment
CELERY_BIN=/home/bitnami/.venv/bin/celery
EOF

sudo mkdir /var/log/celery /var/run/celery
sudo chown bitnami:bitnami /var/log/celery /var/run/celery

sudo systemctl daemon-reload
sudo systemctl enable celeryd
sudo systemctl start celeryd

