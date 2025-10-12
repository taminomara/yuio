var mermaid_config = { startOnLoad: false };

const isDarkMode = window.matchMedia("(prefers-color-scheme: dark)");

let theme = undefined;

function runMermaid() {
  let newTheme = theme;
  switch (document.body.dataset.theme) {
    case "dark":
      newTheme = "dark";
      break;
    case "light":
      newTheme = "default";
      break;
    case "auto":
      newTheme = isDarkMode.matches ? "dark" : "default";
      break;
  }

  if (newTheme === theme) {
    return;
  }

  theme = newTheme;

  console.log(theme);

  mermaid.initialize({ startOnLoad: false, theme: theme, securityLevel: "loose" });

  const items = document.querySelectorAll(".mermaid");
  let counter = 0;
  for (const item of items) {
    const id = counter++;
    if (item.originalCode === undefined) {
      item.originalCode = item.textContent.trim();
    }
    mermaid.render("mermaid" + id, item.originalCode).then(
      (val) => {
        item.innerHTML = val.svg;
      },
      (err) => {
        console.log(err);
      }
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.getElementsByClassName("theme-toggle");
  Array.from(buttons).forEach((btn) =>
    btn.addEventListener("click", runMermaid)
  );
  isDarkMode.addEventListener("change", runMermaid);
  runMermaid();
});
