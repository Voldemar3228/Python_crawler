## Background information

### BeautifulSoup
```
soup = BeautifulSoup(html, "html.parser")
```

Это класс из библиотеки bs4, который:
- принимает HTML-код
- разбирает его в дерево элементов (DOM)
- позволяет удобно искать теги, текст, атрибуты и т.д.

После создания soup ты можешь делать:
- soup.title
- soup.find("a")
- soup.find_all("meta")
- soup.select("div.content")

BeautifulSoup — это инструмент, который превращает этот текст в удобную структуру, чтобы ты мог:
- найти все ссылки
- получить заголовок
- извлечь текст
- получить meta-теги
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

### extract_links
```
for tag in soup.find_all("a", href=True):
```
Находит все теги "a", у которых есть атрибут "href"
```
href = tag["href"].strip()
```
Берёт значение атрибута href и удаляет все лишние пробелы и табуляции
```
absolute_url = urljoin(base_url, href)
```
Получение абсолютной ссылки
Ссылки бывают двух типов:
- относительные ({a href="/about"}), не полный url
- абсолютные
- 
```
parsed = urlparse(absolute_url)
```
Разбираем URL на части.
Например:
```
urlparse("https://example.com/about")
```
вернет 
```
scheme='https'
netloc='example.com'
path='/about'
```

### Обработка ошибок

_safe_extract — это вспомогательная функция-обёртка,
которая безопасно запускает любой метод парсинга и 
не даёт всей программе упасть, если внутри произошла ошибка.

1) func - функция, которую мы хотим запустить
2) *args - аргументы, которые мы передаём в эту функцию (soup, url)
3) default - Значение, которое вернуть, если произошла ошибка
   - для текста → ""
   - для ссылок → []
   - для metadata → {}

Пример вызова:
```commandline
result["links"] = self._safe_extract(
    self.extract_links,
    soup,
    url,
    default=[]
)
```