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
const MOBILE_SHEET_HEIGHT_VAR = "--mobile-sheet-height";

export function createListPanel(elements: ListPanelElements) {
  let startY = 0;
  let startHeight = 0;

  const isMobileResultsState = (): boolean => document.body.classList.contains("mobile-results");

  const setMobileSheetHeight = (ratio: number): void => {
    const clamped = Math.min(0.9, Math.max(0.12, ratio));
    document.body.style.setProperty(MOBILE_SHEET_HEIGHT_VAR, `${Math.round(clamped * 100)}vh`);
  };

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
      if (!isMobileResultsState()) {
        return;
      }
      const touchEvent = event as TouchEvent;
      startY = touchEvent.touches[0].clientY;
      startHeight = sidebarEl.getBoundingClientRect().height;
      sidebarEl.style.transition = "none";
    });

    elements.handle?.addEventListener("touchmove", (event: Event) => {
      if (!isMobileResultsState()) {
        return;
      }
      const touchEvent = event as TouchEvent;
      const touchY = touchEvent.touches[0].clientY;
      const deltaY = startY - touchY;
      const newHeight = startHeight + deltaY;

      if (newHeight > window.innerHeight * 0.12 && newHeight < window.innerHeight * 0.9) {
        setMobileSheetHeight(newHeight / window.innerHeight);
      }
    });

    elements.handle.addEventListener("touchend", () => {
      if (!isMobileResultsState()) {
        return;
      }
      sidebarEl.style.transition = "height 0.3s ease-out";
      const currentRatio = sidebarEl.getBoundingClientRect().height / window.innerHeight;
      if (currentRatio >= 0.6) {
        setMobileSheetHeight(snapHeights.expanded);
      } else if (currentRatio <= 0.25) {
        setMobileSheetHeight(snapHeights.collapsed);
      } else {
        setMobileSheetHeight(snapHeights.mid);
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
