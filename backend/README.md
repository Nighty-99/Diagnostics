# Diagnostic backend

Небольшой backend для Tilda-страницы диагностики.

Он делает три вещи:

- принимает результат диагностики по `POST /api/diagnostic-results`;
- сохраняет запись в SQLite;
- отправляет письмо ученику и администратору, если настроен SMTP.

Зависимости не нужны: используется стандартная библиотека Python.

## Локальный запуск

Из корня проекта:

```powershell
python tilda_export/backend/diagnostic_backend.py
```

Backend будет доступен по адресу:

```text
http://127.0.0.1:8788
```

База по умолчанию:

```text
tilda_export/backend/diagnostic_results.sqlite3
```

Проверка:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8788/health" -UseBasicParsing
```

## Настройки окружения

```powershell
$env:DIAGNOSTIC_BACKEND_HOST="127.0.0.1"
$env:DIAGNOSTIC_BACKEND_PORT="8788"
$env:DIAGNOSTIC_DB_PATH="C:\path\diagnostic_results.sqlite3"
$env:DIAGNOSTIC_ALLOWED_ORIGIN="https://shkolainfinita.tilda.ws"

$env:SMTP_HOST="smtp.example.com"
$env:SMTP_PORT="587"
$env:SMTP_USE_TLS="1"
$env:SMTP_USER="user@example.com"
$env:SMTP_PASSWORD="password"
$env:SMTP_FROM="user@example.com"
$env:ADMIN_EMAIL="infinita.studio@mail.ru"
```

Если SMTP не настроен, результат всё равно сохранится в SQLite, но письмо не уйдёт.

## Production

Для реального сайта backend нужно разместить на сервере/VPS/PaaS с HTTPS.

В `tilda_diagnostics_page.html` замените:

```js
window.DIAGNOSTIC_SUBMIT_URL = "https://your-domain.ru/api/diagnostic-results";
```

Если страница вставляется прямо в Тильду, backend должен разрешать origin сайта:

```powershell
$env:DIAGNOSTIC_ALLOWED_ORIGIN="https://shkolainfinita.tilda.ws"
```

## Персональные данные

В базе сохраняются имя, почта, телефон, согласие на обработку персональных данных и отдельный флаг согласия на рекламную рассылку. Перед запуском на реальном сайте проверьте тексты согласий и ссылки на документы с юристом.
