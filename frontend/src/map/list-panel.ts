import type { LandFeature } from "./types";

type ListPanelElements = {
  listContainer: HTMLElement | null;
  navInfo: HTMLElement | null;
  prevBtn: HTMLButtonElement | null;
  nextBtn: HTMLButtonElement | null;
  sidebar: HTMLElement | null;
  handle: Element | null;
};

const snapHeights = {
  collapsed: 0.15,
  mid: 0.4,
  expanded: 0.85
};

export function createListPanel(elements: ListPanelElements) {
  let startY = 0;
  let startHeight = 0;

  const setStatus = (message: string, color = "#999"): void => {
    if (!elements.listContainer) {
      return;
    }

    const status = document.createElement("p");
    status.style.padding = "20px";
    status.style.color = color;
    status.textContent = message;
    elements.listContainer.replaceChildren(status);
  };

  const render = (features: LandFeature[], onItemClick: (index: number) => void): void => {
    if (!elements.listContainer) {
      return;
    }

    elements.listContainer.replaceChildren();

    if (!features.length) {
      setStatus("결과 없음", "red");
      return;
    }

    features.forEach((feature, idx) => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.id = `item-${idx}`;

      const title = document.createElement("strong");
      title.textContent = feature.properties.address || "";

      const lineBreak = document.createElement("br");

      const desc = document.createElement("small");
      desc.textContent = `${feature.properties.land_type || ""} | ${feature.properties.area || ""}㎡`;

      item.appendChild(title);
      item.appendChild(lineBreak);
      item.appendChild(desc);
      item.addEventListener("click", () => onItemClick(idx));
      elements.listContainer?.appendChild(item);
    });
  };

  const setSelected = (index: number): void => {
    document.querySelectorAll(".list-item").forEach((item, idx) => {
      item.classList.toggle("selected", idx === index);
    });
  };

  const updateNavigation = (currentIndex: number, total: number): void => {
    if (elements.navInfo) {
      elements.navInfo.innerText = total > 0 ? `${currentIndex + 1} / ${total}` : "0 / 0";
    }

    if (elements.prevBtn) {
      elements.prevBtn.disabled = currentIndex <= 0;
    }
    if (elements.nextBtn) {
      elements.nextBtn.disabled = currentIndex >= total - 1 || total === 0;
    }

    setSelected(currentIndex);
  };

  const scrollTo = (index: number): void => {
    const selectedEl = document.getElementById(`item-${index}`);
    if (selectedEl) {
      selectedEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };

  const bindNavigation = (onPrev: () => void, onNext: () => void): void => {
    elements.prevBtn?.addEventListener("click", onPrev);
    elements.nextBtn?.addEventListener("click", onNext);
  };

  const initBottomSheet = (): void => {
    if (!elements.handle || !elements.sidebar) {
      return;
    }

    const sidebarEl = elements.sidebar;

    elements.handle.addEventListener("touchstart", (event: Event) => {
      const touchEvent = event as TouchEvent;
      startY = touchEvent.touches[0].clientY;
      startHeight = sidebarEl.offsetHeight;
      sidebarEl.style.transition = "none";
    });

    elements.handle?.addEventListener("touchmove", (event: Event) => {
      const touchEvent = event as TouchEvent;
      const touchY = touchEvent.touches[0].clientY;
      const deltaY = startY - touchY;
      const newHeight = startHeight + deltaY;

      if (newHeight > window.innerHeight * 0.12 && newHeight < window.innerHeight * 0.9) {
        sidebarEl.style.height = `${newHeight}px`;
      }
    });

    elements.handle.addEventListener("touchend", () => {
      sidebarEl.style.transition = "height 0.3s ease-out";
      const currentRatio = sidebarEl.clientHeight / window.innerHeight;
      if (currentRatio >= 0.6) {
        sidebarEl.style.height = `${snapHeights.expanded * 100}vh`;
      } else if (currentRatio <= 0.25) {
        sidebarEl.style.height = `${snapHeights.collapsed * 100}vh`;
      } else {
        sidebarEl.style.height = `${snapHeights.mid * 100}vh`;
      }
    });
  };

  return {
    bindNavigation,
    initBottomSheet,
    render,
    scrollTo,
    setStatus,
    updateNavigation
  };
}

export type ListPanel = ReturnType<typeof createListPanel>;
