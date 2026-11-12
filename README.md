## Запуск

```bash
python -m venv .venv
#.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
copy .env.example .env
python manage.py init-db
python manage.py create-admin   # интерактивно спросит логин, e-mail, пароль
python manage.py run --debug
```

Первый вход — под созданным администратором. Остальные пользователи появляются
через регистрацию на сайте или через раздел «Пользователи» (роль и команду назначает админ).