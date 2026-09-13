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
