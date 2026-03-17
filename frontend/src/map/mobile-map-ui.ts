const MOBILE_HISTORY_KEY = "mobileMapViewState";
const MOBILE_SHEET_HEIGHT_VAR = "--mobile-sheet-height";
const MOBILE_RESULTS_DEFAULT_SHEET_HEIGHT = "25vh";

export type MobileViewState = "home" | "search" | "results";

type InputRefs = {
  regionSearchInput: HTMLInputElement | null;
  minAreaInput: HTMLInputElement | null;
  maxAreaInput: HTMLInputElement | null;
  rentOnlyFilter: HTMLInputElement | null;
};

type MobileMapUiOptions = {
  desktopInputs: InputRefs;
  mobileInputs: InputRefs;
  body: HTMLElement;
  overlay: HTMLElement | null;
  history: History;
  mediaQueryList: MediaQueryList;
};

function readMobileViewState(value: unknown): MobileViewState | null {
  if (value === "home" || value === "search" || value === "results") {
    return value;
  }
  return null;
}

function canSyncInputs(desktopInputs: InputRefs, mobileInputs: InputRefs): boolean {
  return Boolean(
    desktopInputs.regionSearchInput &&
      desktopInputs.minAreaInput &&
      desktopInputs.maxAreaInput &&
      desktopInputs.rentOnlyFilter &&
      mobileInputs.regionSearchInput &&
      mobileInputs.minAreaInput &&
      mobileInputs.maxAreaInput &&
      mobileInputs.rentOnlyFilter
  );
}

export function createMobileMapUi(options: MobileMapUiOptions) {
  let mobileState: MobileViewState = "home";

  const isMobileViewport = (): boolean => options.mediaQueryList.matches;

  const syncDesktopToMobileInputs = (): void => {
    if (!canSyncInputs(options.desktopInputs, options.mobileInputs)) {
      return;
    }

    options.mobileInputs.regionSearchInput!.value = options.desktopInputs.regionSearchInput!.value;
    options.mobileInputs.minAreaInput!.value = options.desktopInputs.minAreaInput!.value;
    options.mobileInputs.maxAreaInput!.value = options.desktopInputs.maxAreaInput!.value;
    options.mobileInputs.rentOnlyFilter!.checked = options.desktopInputs.rentOnlyFilter!.checked;
  };

  const syncMobileToDesktopInputs = (): void => {
    if (!canSyncInputs(options.desktopInputs, options.mobileInputs)) {
      return;
    }

    options.desktopInputs.regionSearchInput!.value = options.mobileInputs.regionSearchInput!.value;
    options.desktopInputs.minAreaInput!.value = options.mobileInputs.minAreaInput!.value;
    options.desktopInputs.maxAreaInput!.value = options.mobileInputs.maxAreaInput!.value;
    options.desktopInputs.rentOnlyFilter!.checked = options.mobileInputs.rentOnlyFilter!.checked;
  };

  const applyViewportState = (): void => {
    options.body.classList.remove("mobile-home", "mobile-search", "mobile-results");

    if (!isMobileViewport()) {
      options.body.style.removeProperty(MOBILE_SHEET_HEIGHT_VAR);
      return;
    }

    options.body.classList.add(`mobile-${mobileState}`);

    if (mobileState === "results") {
      options.body.style.setProperty(MOBILE_SHEET_HEIGHT_VAR, MOBILE_RESULTS_DEFAULT_SHEET_HEIGHT);
    } else {
      options.body.style.removeProperty(MOBILE_SHEET_HEIGHT_VAR);
    }

    if (options.overlay) {
      if (mobileState === "search") {
        options.overlay.removeAttribute("inert");
      } else {
        options.overlay.setAttribute("inert", "");
      }
    }
  };

  const setState = (nextState: MobileViewState, pushHistory = true): void => {
    mobileState = nextState;
    applyViewportState();

    if (!isMobileViewport() || !pushHistory) {
      return;
    }

    const current = options.history.state && typeof options.history.state === "object" ? options.history.state : {};
    options.history.pushState({ ...current, [MOBILE_HISTORY_KEY]: nextState }, "");
  };

  const initHistory = (): void => {
    if (!isMobileViewport()) {
      return;
    }

    const current = options.history.state && typeof options.history.state === "object" ? options.history.state : {};
    options.history.replaceState({ ...current, [MOBILE_HISTORY_KEY]: mobileState }, "");
    applyViewportState();
  };

  const handlePopState = (historyState: unknown): boolean => {
    if (!isMobileViewport()) {
      return false;
    }

    const nextState = readMobileViewState(
      historyState && typeof historyState === "object"
        ? (historyState as Record<string, unknown>)[MOBILE_HISTORY_KEY]
        : null
    );
    if (!nextState) {
      return false;
    }

    setState(nextState, false);
    return true;
  };

  return {
    applyViewportState,
    getState(): MobileViewState {
      return mobileState;
    },
    handlePopState,
    initHistory,
    isMobileViewport,
    setState,
    syncDesktopToMobileInputs,
    syncMobileToDesktopInputs,
  };
}

export type MobileMapUi = ReturnType<typeof createMobileMapUi>;
