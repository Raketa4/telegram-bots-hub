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
