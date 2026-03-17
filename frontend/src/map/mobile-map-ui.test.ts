import { describe, expect, test, vi } from "vitest";

import { createMobileMapUi } from "./mobile-map-ui";

function createInput(): HTMLInputElement {
  return document.createElement("input");
}

function createHistoryStub(): History {
  const historyState: { current: unknown } = { current: null };

  return {
    get state() {
      return historyState.current;
    },
    pushState(data: unknown) {
      historyState.current = data;
    },
    replaceState(data: unknown) {
      historyState.current = data;
    },
  } as unknown as History;
}

function createMediaQueryList(matches: boolean): MediaQueryList {
  return {
    matches,
    media: "(max-width: 768px)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList;
}

describe("createMobileMapUi", () => {
  test("syncs desktop and mobile inputs in both directions", () => {
    const desktopInputs = {
      regionSearchInput: createInput(),
      minAreaInput: createInput(),
      maxAreaInput: createInput(),
      rentOnlyFilter: createInput(),
    };
    const mobileInputs = {
      regionSearchInput: createInput(),
      minAreaInput: createInput(),
      maxAreaInput: createInput(),
      rentOnlyFilter: createInput(),
    };
    desktopInputs.rentOnlyFilter.type = "checkbox";
    mobileInputs.rentOnlyFilter.type = "checkbox";

    desktopInputs.regionSearchInput.value = "대산읍";
    desktopInputs.minAreaInput.value = "100";
    desktopInputs.maxAreaInput.value = "500";
    desktopInputs.rentOnlyFilter.checked = true;

    const overlay = document.createElement("div");
    overlay.setAttribute("inert", "");

    const mobileUi = createMobileMapUi({
      desktopInputs,
      mobileInputs,
      body: document.body,
      overlay,
      history: createHistoryStub(),
      mediaQueryList: createMediaQueryList(true),
    });

    mobileUi.syncDesktopToMobileInputs();
    expect(mobileInputs.regionSearchInput.value).toBe("대산읍");
    expect(mobileInputs.minAreaInput.value).toBe("100");
    expect(mobileInputs.maxAreaInput.value).toBe("500");
    expect(mobileInputs.rentOnlyFilter.checked).toBe(true);

    mobileInputs.regionSearchInput.value = "동문동";
    mobileInputs.minAreaInput.value = "10";
    mobileInputs.maxAreaInput.value = "20";
    mobileInputs.rentOnlyFilter.checked = false;

    mobileUi.syncMobileToDesktopInputs();
    expect(desktopInputs.regionSearchInput.value).toBe("동문동");
    expect(desktopInputs.minAreaInput.value).toBe("10");
    expect(desktopInputs.maxAreaInput.value).toBe("20");
    expect(desktopInputs.rentOnlyFilter.checked).toBe(false);
  });

  test("applies mobile results state and restores state from popstate", () => {
    const overlay = document.createElement("div");
    overlay.setAttribute("inert", "");
    const history = createHistoryStub();
    const mobileUi = createMobileMapUi({
      desktopInputs: {
        regionSearchInput: null,
        minAreaInput: null,
        maxAreaInput: null,
        rentOnlyFilter: null,
      },
      mobileInputs: {
        regionSearchInput: null,
        minAreaInput: null,
        maxAreaInput: null,
        rentOnlyFilter: null,
      },
      body: document.body,
      overlay,
      history,
      mediaQueryList: createMediaQueryList(true),
    });

    mobileUi.setState("results", true);
    expect(document.body.classList.contains("mobile-results")).toBe(true);
    expect(document.body.style.getPropertyValue("--mobile-sheet-height")).toBe("25vh");

    mobileUi.setState("search", false);
    expect(overlay.hasAttribute("inert")).toBe(false);

    expect(mobileUi.handlePopState({ mobileMapViewState: "home" })).toBe(true);
    expect(document.body.classList.contains("mobile-home")).toBe(true);
    expect(history.state).toEqual({ mobileMapViewState: "results" });
  });
});
