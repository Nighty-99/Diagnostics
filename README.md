# Tilda diagnostics export

Это отдельная версия страницы диагностики для сайта на Тильде.

Текущий Streamlit-проект не меняется. В папке лежат копии JSON-диагностик и отдельная HTML-страница:

- `tilda_diagnostics_page.html`
- `diagnostics/*.json`
- `backend/diagnostic_backend.py`

## Как проверить локально

Из корня проекта запустите backend для сохранения результатов:

```powershell
python tilda_export/backend/diagnostic_backend.py
```

В другом терминале запустите простой локальный сервер для страницы:

```powershell
python -m http.server 8787 -d tilda_export
```

Откройте:

```text
http://127.0.0.1:8787/tilda_diagnostics_page.html
```

Открывать HTML двойным кликом не стоит: браузер может заблокировать загрузку JSON через `fetch`.

Локально страница отправляет результат на:

```text
http://127.0.0.1:8788/api/diagnostic-results
```

SQLite-база создаётся здесь:

```text
tilda_export/backend/diagnostic_results.sqlite3
```

## Как перенести в Тильду

Вариант 1: загрузить `tilda_diagnostics_page.html` и JSON-файлы на свой хостинг, а в Тильде вставить iframe.

Вариант 2: вставить HTML-код страницы в блок `T123 HTML-код`, а JSON-файлы загрузить в файловое хранилище/на хостинг. После загрузки замените в HTML массив:

```js
window.DIAGNOSTIC_CONFIG_URLS = [
  "diagnostics/ege_math_10_base_readiness_config.json",
  ...
];
```

на абсолютные ссылки к загруженным JSON-файлам.

Для сохранения результатов и отправки писем нужен backend с HTTPS. После размещения backend замените в HTML:

```js
window.DIAGNOSTIC_SUBMIT_URL = "https://your-domain.ru/api/diagnostic-results";
```

Подробности по backend: `backend/README.md`.

## Дизайн

Страница стилизована под текущий сайт Infinita:

- заголовки: `Cormorant`;
- основной текст: `Inter`;
- основной акцент: `#cf294b`;
- вторичный акцент: `#ff8562`;
- тёмная верхняя секция с градиентом;
- прямые углы и строгие CTA-кнопки в стиле сайта.

Если палитра сайта изменится, основные цвета находятся в начале CSS внутри `:root`.

## Важно

HTML-версия проверяет ответы в браузере. Это удобно для Тильды, но правильные ответы технически видны в исходном коде или JSON-файлах. Backend в этой папке сохраняет результаты и отправляет письма, но не скрывает правильные ответы. Для полностью закрытой проверки нужен серверный расчёт ответов.
