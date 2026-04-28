# BXM Management — Инструкция для ИИ-агента

## Что это за проект
Веб-дашборд для управления заявками на технику по BXM-филиалам.
Готовый файл: `bxm_complete.html` — содержит полный UI: логин, дашборд, аналитику, поддержку.

---

## Дизайн-система (не менять без причины)

| Токен | Значение | Использование |
|---|---|---|
| `--clr-primary` | `#3525cd` | Кнопки, активные состояния, акценты |
| `--clr-primary-light` | `#e2dfff` | Фоны бейджей, hover-состояния |
| `--clr-bg` | `#f8f9ff` | Фон страниц |
| `--clr-surface` | `#ffffff` | Карточки, панели |
| `--clr-text` | `#0b1c30` | Основной текст |
| `--clr-text-hint` | `#777587` | Подписи, плейсхолдеры |
| `--clr-border-light` | `#e5eeff` | Разделители, границы |
| Шрифт | `Inter` | Все уровни типографики |
| Радиус | `--radius-lg: 12px` | Карточки; `--radius-md: 8px` — поля/кнопки |

**Правило:** все цвета через CSS-переменные, никаких хардкод hex вне блока `:root`.

---

## Структура файла

```
bxm_complete.html
├── <style>              — весь CSS (токены → компоненты)
├── #page-login          — страница входа
├── #page-shell          — оболочка с сайдбаром
│   ├── .sidebar         — навигация + экспорт + выход
│   └── .main-content
│       ├── #sub-dashboard   — обзор заявок
│       ├── #sub-analytics   — графики
│       └── #sub-support     — форма обращения
└── <script>
    ├── DATA LAYER       — заменить на fetch() к API
    ├── APP STATE        — фильтры, пагинация
    ├── ROUTER           — переключение страниц
    ├── DROPDOWNS        — филиал / дата
    ├── TABLE            — рендер + пагинация
    └── CHARTS           — Chart.js bar + donut
```

---

## Что нужно адаптировать под реальный проект

### 1. Замена моковых данных на API

Найди в `<script>` блок `/* DATA LAYER */` и замени функцию `seed()` на реальный fetch:

```javascript
// БЫЛО (мок):
let ALL_TICKETS = [];
(function seed(){ BRANCHES.forEach(b=>{ ... }) })();

// СТАЛО (реальный API):
let ALL_TICKETS = [];
async function loadTickets() {
  const res = await fetch('/api/tickets', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
  });
  ALL_TICKETS = await res.json();
  renderTable();
  buildBranchList();
  buildLoctypeCards();
}
```

### 2. Авторизация (логин)

Найди функцию `loginSubmit()` и замени на:

```javascript
async function loginSubmit(e) {
  e.preventDefault();
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email:    document.getElementById('l-email').value,
      password: document.getElementById('l-pass').value
    })
  });
  if (res.ok) {
    const { token } = await res.json();
    localStorage.setItem('token', token);
    document.getElementById('page-login').classList.remove('active');
    document.getElementById('page-shell').classList.add('active');
    showSub('dashboard');
    await loadTickets();
  } else {
    // показать ошибку пользователю
    alert('Неверный логин или пароль');
  }
}
```

### 3. Экспорт отчёта

Найди функцию `doExport()` и замени на:

```javascript
function doExport() {
  const params = new URLSearchParams({
    branch: selBranch || '',
    loctype: selLT || '',
    type: filterType,
    from: dFrom || '',
    to: dTo || ''
  });
  window.open('/api/export?' + params.toString(), '_blank');
}
```

### 4. Разбивка на компоненты (если нужен фреймворк)

Если проект на **React / Vue / Svelte** — каждый блок CSS легко становится компонентом:

| CSS-класс | Компонент |
|---|---|
| `.stat-card` | `<StatCard>` |
| `.table-card` + `.data-table` | `<TicketsTable>` |
| `.dd-panel` + `.dd-trigger` | `<Dropdown>` |
| `.badge-*` | `<StatusBadge status="pending">` |
| `.sidebar` | `<Sidebar>` |
| `.chart-card` | `<ChartCard>` |

### 5. Список API эндпоинтов (заполни под свой бэкенд)

```
POST /api/auth/login          — { email, password } → { token }
GET  /api/tickets             — ?branch=&type=&from=&to= → Ticket[]
GET  /api/branches            — → Branch[]
GET  /api/stats               — → { total, pending, approved, rejected }
GET  /api/export              — ?params → file download
```

---

## Структура объекта Ticket (текущая)

```typescript
interface Ticket {
  id:      number;       // номер заявки
  bn:      string;       // название филиала
  bc:      string;       // код BXM (BXM01 ... BXM40)
  lt:      'city' | 'regional';
  type:    'replacement' | 'new' | 'repair';
  dev:     string;       // название устройства
  inv:     string;       // инвентарный код (INV-xxxxx / PRN-xxxxx)
  emp:     string;       // ФИО сотрудника
  init:    string;       // инициалы для аватара
  year:    number;       // год выдачи техники
  status:  'pending' | 'approved' | 'rejected' | 'repair' | 'processing';
  ds:      string;       // дата отображения "12 Apr 2025"
  dv:      string;       // дата для фильтра "2025-04-12"
}
```

---

## Структура объекта Branch

```typescript
interface Branch {
  n:  string;              // название "Алатауский"
  c:  string;              // BXM-код "BXM02"
  lt: 'city' | 'regional'; // тип филиала
}
```

---

## Ключевые функции JS (для агента)

| Функция | Что делает |
|---|---|
| `renderTable()` | Перерисовывает таблицу заявок с учётом всех фильтров |
| `getFiltered()` | Возвращает отфильтрованный массив заявок |
| `buildBranchList()` | Строит алфавитный список филиалов в дропдауне |
| `buildLoctypeCards()` | Строит карточки Городской/Региональный |
| `toggleDD(panelId, arrowId)` | Открывает/закрывает дропдаун |
| `showSub(name)` | Переключает страницу: 'dashboard' / 'analytics' / 'support' |
| `initCharts()` | Инициализирует Chart.js (вызывается один раз) |
| `loginSubmit(e)` | Обработчик формы входа |
| `logout()` | Выход — очищает токен и показывает логин |

---

## Промпт для быстрого старта (скопируй агенту)

```
У меня есть готовый HTML-файл bxm_complete.html с полным UI для дашборда BXM Management.
Дизайн-система, все стили и логика уже реализованы.

Задача: адаптировать под реальный бэкенд.
Стек бэкенда: [УКАЖИ СВОЙ — например Python FastAPI / Node.js Express / Django]
База данных: [УКАЖИ — PostgreSQL / MongoDB / SQLite]

Что нужно сделать:
1. Заменить моковые данные (функция seed() в DATA LAYER) на fetch() к API
2. Подключить реальную авторизацию в loginSubmit()
3. Реализовать эндпоинты согласно интерфейсам Ticket и Branch из AGENT_INSTRUCTIONS.md
4. Подключить экспорт отчёта в doExport()

НЕ менять: CSS-переменные, структуру классов, дизайн компонентов.
```
