# Деплой на DigitalOcean

Пошаговая инструкция: новый droplet, перенос текущей локальной базы целиком,
доступ для команды по логину/паролю поверх HTTPS.

## 0. Что уже готово в репозитории

- `app.py` — конфиг (БД, авторизация) теперь берётся из `.env`, дефолтного
  пароля к базе больше нет.
- `requirements.txt` — зависимости для сервера.
- `deploy/provision.sh` — разово настраивает чистый droplet (Postgres, nginx,
  firewall, системный пользователь, роль и база в Postgres).
- `deploy/dump_db.sh` — локально: снимает дамп текущей базы.
- `deploy/restore_db.sh` — на сервере: разворачивает дамп в базу.
- `deploy/agent-licence.service` — systemd-юнит (gunicorn).
- `deploy/nginx.conf` — reverse proxy + заготовка под TLS.

## 1. Создать droplet

В панели DigitalOcean (или `doctl compute droplet create`, если поставите
`doctl` и авторизуетесь токеном):

- Image: **Ubuntu 22.04 (LTS) x64**
- Plan: Basic, 1 GB RAM / 1 vCPU достаточно для этого приложения
- Region: ближайший к вам/команде
- Authentication: **SSH key** (не пароль)
- Добавьте droplet в тот же VPC/проект, что и остальные ваши серверы, если это важно

После создания запишите **IP droplet'а** — он понадобится дальше.

## 2. Первый вход и bootstrap

```bash
ssh root@<IP_ДРОПЛЕТА>
```

На сервере:

```bash
git clone https://github.com/Leillaa/Heresure_Search.git /root/repo-tmp
cp -r /root/repo-tmp/deploy /root/deploy
cd /root/deploy

# придумайте пароль для роли БД приложения, например:
openssl rand -base64 24
# сохраните его — понадобится в п.4

bash provision.sh '<ПАРОЛЬ_ИЗ_ПРЕДЫДУЩЕЙ_СТРОКИ>'
```

Скрипт поставит Postgres/nginx/python, включит firewall (открыты только
SSH + 80/443), создаст системного пользователя `agentapp`, роль
`agents_app` и пустую базу `Agents_Heresure`.

## 3. Залить код приложения

Проще всего — тем же git (репозиторий приватный/публичный, но помните: в его
истории уже светился старый пароль `1560`, см. предупреждение ниже):

```bash
sudo -u agentapp git clone https://github.com/Leillaa/Heresure_Search.git /opt/agent_licence
cd /opt/agent_licence
sudo -u agentapp python3 -m venv .venv
sudo -u agentapp .venv/bin/pip install -r requirements.txt
```

Создайте `.env` в `/opt/agent_licence/.env` (владелец — `agentapp`,
права `600`), по образцу `.env.example`:

```bash
sudo -u agentapp cp .env.example .env
sudo -u agentapp nano .env
```

Заполните:
- `PGUSER=agents_app`, `PGDATABASE=Agents_Heresure`, `PGPASSWORD=<пароль из п.2>`
- `SMTP_*` — если рассылку тоже будете гонять с сервера
- `BASIC_AUTH_USERS` оставьте закомментированной — сайт пока открыт всем по
  ссылке, без логина/пароля (можно включить позже, см. комментарий в файле)

```bash
sudo chmod 600 /opt/agent_licence/.env
```

## 4. Перенести базу (все текущие записи)

**Локально**, у себя на маке:

```bash
cd ~/Desktop/agent_licence
./deploy/dump_db.sh
# создаст файл вида agents_heresure_20260817_153000.dump
scp agents_heresure_*.dump root@<IP_ДРОПЛЕТА>:/root/
```

**На сервере**:

```bash
cd /opt/agent_licence
PGPASSWORD='<пароль роли agents_app>' \
  deploy/restore_db.sh /root/agents_heresure_20260817_153000.dump
```

Скрипт восстановит схему и все строки и в конце покажет `SELECT COUNT(*)` —
сверьте с тем, что видите локально в `http://127.0.0.1:5000`.

## 5. Запустить приложение как сервис

```bash
sudo cp /opt/agent_licence/deploy/agent-licence.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now agent-licence
sudo systemctl status agent-licence   # должен быть active (running)
```

## 6. nginx + HTTPS

Домена нет — используем бесплатный wildcard-DNS `sslip.io`, который сам
резолвится в IP droplet'а без всякой покупки домена: `<IP>.sslip.io`
(например `167.99.12.34.sslip.io`).

```bash
sudo cp /opt/agent_licence/deploy/nginx.conf /etc/nginx/sites-available/agent-licence
sudo sed -i "s/YOUR_HOST/<IP_ДРОПЛЕТА_ЧЕРЕЗ_ТОЧКИ>.sslip.io/" /etc/nginx/sites-available/agent-licence
sudo ln -s /etc/nginx/sites-available/agent-licence /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <IP_ДРОПЛЕТА_ЧЕРЕЗ_ТОЧКИ>.sslip.io
```

Certbot сам допишет TLS-блок и настроит редирект с http на https.

Готово: `https://<IP>.sslip.io` — это и есть ваш адрес сайта. Открывается
с любого устройства простым переходом по ссылке, без логина и пароля.
Домен не покупали — `sslip.io` бесплатно резолвит `<IP>.sslip.io` в IP
droplet'а, этого достаточно и для certbot (настоящий TLS-сертификат).

Если позже захотите свой домен (например `agents.вашкомпания.com`) — просто
направьте A-запись на IP droplet'а и перевыпустите сертификат:
`certbot --nginx -d agents.вашкомпания.com`.

## 7. Проверка и дальнейшие обновления

Сначала один раз — локально запомнить адрес сервера (файл в `.gitignore`,
в git не попадает):

```bash
cp deploy/server.env.example deploy/server.env
# впишите туда SERVER_IP и SITE_URL этого droplet'а
```

- Логи сайта: `journalctl -u agent-licence -f`
- Обновить код после правок — локально, одной командой: `./deploy/update.sh`
  (rsync на сервер + `systemctl restart agent-licence`, `.env` на сервере не трогает)

## 8. Ежедневная догрузка новых агентов (parser.py по расписанию)

На сервере настроен systemd-таймер, который каждый день в **9:00 по
Нью-Йорку** (America/New_York, DST учитывается автоматически) сам:
скачивает свежий реестр Florida DFS → фильтрует под условия (Broward/
Miami-Dade, life-лицензии) → добавляет в `licenses` только новых агентов
(по паре Full Name + Business Email) с `checked = false`. Уже
существующие записи и выставленные вручную `checked`/`Personal Email`
не трогает.

Единоразовая установка (если ставите на новый сервер — на этом уже стоит):

```bash
cp /opt/agent_licence/deploy/agent-licence-parser.service /opt/agent_licence/deploy/agent-licence-parser.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now agent-licence-parser.timer
```

Полезные команды:
- Когда следующий запуск: `systemctl list-timers agent-licence-parser.timer`
- Логи последнего прогона: `journalctl -u agent-licence-parser.service -n 50`
- Запустить прямо сейчас, не дожидаясь 9 утра: `systemctl start agent-licence-parser.service`
  (это тот же oneshot-сервис, что триггерит таймер; статус "inactive (dead)"
  после запуска — это нормально, так и должно быть для oneshot)

## ⚠️ Про утёкший пароль `1560`

Он был захардкожен как дефолт в `app.py`/`parser.py`/`send_campaign.py` и
уже закоммичен в git, запушенный в `github.com/Leillaa/Heresure_Search`.
Я убрал хардкод и на сервере используется новый случайный пароль — но сам
факт, что `1560` есть в истории репозитория, никуда не делся. Если это
единственное место, где использовался этот пароль (например, локальный
Postgres только у вас на маке) — можно просто его больше нигде не
использовать. Если хотите вычистить его из истории git — скажите, помогу
(`git filter-repo` + force-push, это уже необратимая операция над историей,
делаем только по явному запросу).
