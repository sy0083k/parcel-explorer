export function initAdminTabs(onStatsSelected: () => void): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>(".nav button");
  const panels: Record<string, HTMLElement | null> = {
    upload: document.getElementById("panel-upload"),
    settings: document.getElementById("panel-settings"),
    password: document.getElementById("panel-password"),
    stats: document.getElementById("panel-stats")
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");

      const name = tab.dataset.tab || "upload";
      Object.values(panels).forEach((panel) => panel?.classList.remove("active"));
      panels[name]?.classList.add("active");

      if (name === "stats") {
        onStatsSelected();
      }
    });
  });
}
