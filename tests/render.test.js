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
