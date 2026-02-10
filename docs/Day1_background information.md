## Background information

```
async with self.session.get(url) as response:
```

1. self.session — объект сессии HTTP
2. .get(url) — отправка HTTP-запроса GET на указанный url
3. async with ... as response - асинхронный контекстный менеджер
    - открывает соединение
    - выполняет запрос
    - кладёт ответ в переменную response
    - гарантированно закрывает соединение, когда блок закончится

response — это объект ответа сервера. У него есть полезные поля:
- response.status      # HTTP-код (200, 404 и т.д.)
- response.headers     # заголовки
- await response.text()  # тело ответа (строкой)
- await response.json()  # если JSON
- await response.read()  # байты

```
tasks = [asyncio.create_task(_fetch(url)) for url in urls]
```
1. _fetch(url) — корутина (ещё не запущена)
2. asyncio.create_task(...):
    - планирует её выполнение в event loop
    - запускает сразу, не дожидаясь await
    - возвращает объект Task

Если urls = 100, ты сразу создаёшь 100 задач
(а semaphore внутри fetch_url ограничивает реальное количество одновременных запросов)
```
results = await asyncio.gather(*tasks)
```
Что делает asyncio.gather
- ждёт, пока все задачи завершатся
- собирает результаты в том же порядке, что и tasks
- возвращает список результатов