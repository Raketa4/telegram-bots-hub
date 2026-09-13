# telegram-bots-hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Одностраничный статический сайт с 10 кнопками, каждая из которых либо ведёт на `t.me/<bot_username>`, либо показана неактивной с подписью «скоро», и его публикация на GitHub Pages.

**Architecture:** Чистый HTML/CSS/JS без сборки. Конфиг ботов (`js/bots.js`) и чистая функция вычисления состояния кнопки (`js/render.js`) тестируются напрямую через Node (`assert`, без npm-зависимостей); DOM-склейка (`js/main.js`) и вёрстка проверяются вручную в браузере.

**Tech Stack:** HTML5, CSS3, vanilla JS (без модулей сборки, без npm), Node.js только для запуска тестов через `node`, `gh` CLI для GitHub.

**Spec:** `docs/superpowers/specs/2026-09-13-telegram-bots-hub-design.md`

## Global Constraints

- Чистый HTML/CSS/JS, без сборки и фреймворков, без npm-зависимостей.
- `username === null` → кнопка неактивна (disabled), серая, подпись «скоро».
- `username` задан → кнопка становится ссылкой `<a href="https://t.me/<username>" target="_blank" rel="noopener">`.
- Никакого backend/webhook — кнопки только открывают `t.me/<bot>`.
- Деплой: GitHub-репозиторий `Raketa4/telegram-bots-hub`, GitHub Pages из ветки `main`, корень. Итоговый URL: `https://raketa4.github.io/telegram-bots-hub/`.

---

### Task 1: Чистая функция состояния кнопки (`render.js`)

**Files:**
- Create: `js/render.js`
- Test: `tests/render.test.js`

**Interfaces:**
- Produces: `buttonState(bot)` — принимает `{id, title, username}`, возвращает:
  - если `username` задан: `{ active: true, label: bot.title, href: "https://t.me/" + bot.username }`
  - если `username === null`: `{ active: false, label: bot.title, href: null, note: "скоро" }`
  - Экспортируется как `module.exports = { buttonState }` в Node и как глобальная функция `buttonState` в браузере (без модулей).

- [ ] **Step 1: Написать падающий тест**

Создать `tests/render.test.js`:

```js
const assert = require("assert");
const { buttonState } = require("../js/render.js");

// Активный бот
{
  const state = buttonState({ id: 1, title: "Кнопка 1", username: "my_learning_bot" });
  assert.strictEqual(state.active, true);
  assert.strictEqual(state.label, "Кнопка 1");
  assert.strictEqual(state.href, "https://t.me/my_learning_bot");
}

// Бот ещё не создан
{
  const state = buttonState({ id: 2, title: "Кнопка 2", username: null });
  assert.strictEqual(state.active, false);
  assert.strictEqual(state.label, "Кнопка 2");
  assert.strictEqual(state.href, null);
  assert.strictEqual(state.note, "скоро");
}

console.log("render.test.js: OK");
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `node tests/render.test.js`
Expected: FAIL — `Cannot find module '../js/render.js'`

- [ ] **Step 3: Реализовать `js/render.js`**

```js
function buttonState(bot) {
  if (bot.username) {
    return {
      active: true,
      label: bot.title,
      href: "https://t.me/" + bot.username,
    };
  }
  return {
    active: false,
    label: bot.title,
    href: null,
    note: "скоро",
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { buttonState };
}
```

- [ ] **Step 4: Запустить тест и убедиться, что он проходит**

Run: `node tests/render.test.js`
Expected: `render.test.js: OK`

- [ ] **Step 5: Commit**

```bash
git add js/render.js tests/render.test.js
git commit -m "Add buttonState render logic with tests"
```

---

### Task 2: Конфиг ботов (`bots.js`)

**Files:**
- Create: `js/bots.js`
- Test: `tests/bots.test.js`

**Interfaces:**
- Consumes: ничего (данные).
- Produces: `BOTS` — массив из 10 объектов `{ id: number, title: string, username: string|null }`, `id` от 1 до 10 по порядку, `title` = `"Кнопка " + id`, `username: null` для всех (боты ещё не созданы). Экспортируется как `module.exports = { BOTS }` в Node и как глобальный `const BOTS` в браузере.

- [ ] **Step 1: Написать падающий тест**

Создать `tests/bots.test.js`:

```js
const assert = require("assert");
const { BOTS } = require("../js/bots.js");

assert.strictEqual(BOTS.length, 10);

BOTS.forEach((bot, index) => {
  const expectedId = index + 1;
  assert.strictEqual(bot.id, expectedId);
  assert.strictEqual(bot.title, "Кнопка " + expectedId);
  assert.strictEqual(bot.username, null);
});

console.log("bots.test.js: OK");
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `node tests/bots.test.js`
Expected: FAIL — `Cannot find module '../js/bots.js'`

- [ ] **Step 3: Реализовать `js/bots.js`**

```js
const BOTS = [
  { id: 1, title: "Кнопка 1", username: null },
  { id: 2, title: "Кнопка 2", username: null },
  { id: 3, title: "Кнопка 3", username: null },
  { id: 4, title: "Кнопка 4", username: null },
  { id: 5, title: "Кнопка 5", username: null },
  { id: 6, title: "Кнопка 6", username: null },
  { id: 7, title: "Кнопка 7", username: null },
  { id: 8, title: "Кнопка 8", username: null },
  { id: 9, title: "Кнопка 9", username: null },
  { id: 10, title: "Кнопка 10", username: null },
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { BOTS };
}
```

- [ ] **Step 4: Запустить тест и убедиться, что он проходит**

Run: `node tests/bots.test.js`
Expected: `bots.test.js: OK`

- [ ] **Step 5: Commit**

```bash
git add js/bots.js tests/bots.test.js
git commit -m "Add BOTS config with 10 placeholder buttons"
```

---

### Task 3: HTML-каркас и стили

**Files:**
- Create: `index.html`
- Create: `css/style.css`

**Interfaces:**
- Consumes: ничего от предыдущих задач напрямую (JS подключается в Task 4).
- Produces: контейнер `<div id="buttons-container"></div>` в `index.html`, куда Task 4 будет вставлять кнопки; CSS-классы `.bot-button` (общий), `.bot-button--active` (кликабельная), `.bot-button--inactive` (серая, disabled).

- [ ] **Step 1: Создать `index.html`**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Telegram Bots Hub</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <main>
    <h1>Мои обучающие Telegram-боты</h1>
    <p class="subtitle">Каждая кнопка — отдельный бот. Пока бот не создан, кнопка неактивна.</p>
    <div id="buttons-container"></div>
  </main>
  <script src="js/bots.js"></script>
  <script src="js/render.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Создать `css/style.css`**

```css
:root {
  color-scheme: light dark;
  --bg: #0f1115;
  --card-bg: #1b1f27;
  --text: #e8e8e8;
  --muted: #8a8f98;
  --accent: #34a1eb;
  --accent-hover: #2688cc;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

main {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 20px;
  text-align: center;
}

h1 {
  font-size: 1.8rem;
  margin-bottom: 8px;
}

.subtitle {
  color: var(--muted);
  margin-bottom: 32px;
}

#buttons-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.bot-button {
  display: block;
  padding: 20px 12px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  border: none;
  cursor: pointer;
}

.bot-button--active {
  background: var(--accent);
  color: #fff;
}

.bot-button--active:hover {
  background: var(--accent-hover);
}

.bot-button--inactive {
  background: var(--card-bg);
  color: var(--muted);
  cursor: not-allowed;
}

.bot-button--inactive .bot-button__note {
  display: block;
  font-size: 0.75rem;
  font-weight: 400;
  margin-top: 4px;
}
```

- [ ] **Step 3: Ручная проверка**

Открыть `index.html` напрямую в браузере (Windows: `start index.html` из папки проекта). Убедиться, что видны заголовок и пустой контейнер `#buttons-container` (кнопок пока нет — они появятся в Task 4). Ошибок в консоли браузера по загрузке CSS быть не должно.

- [ ] **Step 4: Commit**

```bash
git add index.html css/style.css
git commit -m "Add HTML shell and styles"
```

---

### Task 4: Рендер кнопок на странице (`main.js`)

**Files:**
- Create: `js/main.js`

**Interfaces:**
- Consumes: `BOTS` (глобальный массив из Task 2), `buttonState(bot)` (глобальная функция из Task 1), `#buttons-container` (из Task 3), CSS-классы `.bot-button`, `.bot-button--active`, `.bot-button--inactive`, `.bot-button__note` (из Task 3).
- Produces: заполняет `#buttons-container` DOM-элементами при загрузке страницы.

- [ ] **Step 1: Реализовать `js/main.js`**

```js
function renderBots(bots, container) {
  container.innerHTML = "";

  bots.forEach((bot) => {
    const state = buttonState(bot);
    let el;

    if (state.active) {
      el = document.createElement("a");
      el.href = state.href;
      el.target = "_blank";
      el.rel = "noopener";
      el.className = "bot-button bot-button--active";
      el.textContent = state.label;
    } else {
      el = document.createElement("button");
      el.type = "button";
      el.disabled = true;
      el.className = "bot-button bot-button--inactive";
      el.textContent = state.label;

      const note = document.createElement("span");
      note.className = "bot-button__note";
      note.textContent = state.note;
      el.appendChild(note);
    }

    container.appendChild(el);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("buttons-container");
  renderBots(BOTS, container);
});
```

- [ ] **Step 2: Ручная проверка в браузере**

Открыть (или перезагрузить) `index.html` в браузере. Убедиться, что:
- отрисовано ровно 10 кнопок с подписями «Кнопка 1» … «Кнопка 10»;
- все кнопки серые, задизейблены, под подписью — надпись «скоро»;
- в консоли браузера (DevTools → Console) нет ошибок.

- [ ] **Step 3: Проверить, что задел под будущего бота работает**

В `js/bots.js` временно поменять `{ id: 1, title: "Кнопка 1", username: null }` на `{ id: 1, title: "Кнопка 1", username: "test_bot" }`, перезагрузить страницу и убедиться, что кнопка 1 стала синей активной ссылкой на `https://t.me/test_bot`. Затем вернуть `username: null` обратно (это временная ручная проверка, коммитить изменение не нужно).

- [ ] **Step 4: Commit**

```bash
git add js/main.js
git commit -m "Render bot buttons into the page from config"
```

---

### Task 5: Публикация на GitHub Pages

**Files:**
- Modify: (нет новых файлов; работа с git remote и GitHub API через `gh`)

**Interfaces:**
- Consumes: локальный репозиторий `telegram-bots-hub` со всеми коммитами из Task 1–4.
- Produces: публичный репозиторий `Raketa4/telegram-bots-hub` на GitHub и включённый GitHub Pages по адресу `https://raketa4.github.io/telegram-bots-hub/`.

- [ ] **Step 1: Создать репозиторий на GitHub и запушить**

```bash
gh repo create Raketa4/telegram-bots-hub --public --source=. --remote=origin --push
```

- [ ] **Step 2: Включить GitHub Pages из ветки `main`, корень**

```bash
gh api repos/Raketa4/telegram-bots-hub/pages -X POST -f "source[branch]=main" -f "source[path]=/"
```

Expected: JSON-ответ с `"html_url": "https://raketa4.github.io/telegram-bots-hub/"` (или похожий), либо `204`/успешный статус без ошибок.

- [ ] **Step 3: Проверить, что сайт опубликован**

Подождать 1-2 минуты (GitHub Pages деплоится не мгновенно), затем:

```bash
curl -s -o /dev/null -w "%{http_code}" https://raketa4.github.io/telegram-bots-hub/
```

Expected: `200`

- [ ] **Step 4: Commit (если появились изменения, например .gitignore)**

Если `gh repo create` не внёс изменений в рабочее дерево — коммитить нечего, шаг пропускается. Если `git status` показывает изменения — закоммитить их с сообщением `"Finalize repo setup for GitHub Pages"`.
