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
