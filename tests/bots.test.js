const assert = require("assert");
const { BOTS } = require("../js/bots.js");

assert.strictEqual(BOTS.length, 10);

const honeyShop = BOTS[0];
assert.strictEqual(honeyShop.id, 1);
assert.strictEqual(honeyShop.title, "Магазин мёда (тест)");
assert.strictEqual(typeof honeyShop.username, "string");
assert.ok(honeyShop.username.length > 0);

BOTS.slice(1).forEach((bot, index) => {
  const expectedId = index + 2;
  assert.strictEqual(bot.id, expectedId);
  assert.strictEqual(bot.title, "Кнопка " + expectedId);
  assert.strictEqual(bot.username, null);
});

console.log("bots.test.js: OK");
