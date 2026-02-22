import type { LandFeature } from "./types";

type FilterElements = {
  regionSearchInput: HTMLInputElement | null;
  minAreaInput: HTMLInputElement | null;
  maxAreaInput: HTMLInputElement | null;
  rentOnlyFilter: HTMLInputElement | null;
};

export type FilterValues = {
  isRentOnly: boolean;
  rawSearchTerm: string;
  searchTerm: string;
  rawMinAreaInput: string;
  rawMaxAreaInput: string;
  minArea: number;
  maxArea: number;
};

export function createFilters(elements: FilterElements) {
  const getValues = (): FilterValues => {
    const rawSearchTerm = elements.regionSearchInput?.value ?? "";
    const searchTerm = rawSearchTerm.trim();
    const rawMinAreaInput = elements.minAreaInput?.value ?? "";
    const rawMaxAreaInput = elements.maxAreaInput?.value ?? "";

    return {
      isRentOnly: Boolean(elements.rentOnlyFilter?.checked),
      rawSearchTerm,
      searchTerm,
      rawMinAreaInput,
      rawMaxAreaInput,
      minArea: Number.parseFloat(rawMinAreaInput || "") || 0,
      maxArea: Number.parseFloat(rawMaxAreaInput || "") || Number.POSITIVE_INFINITY
    };
  };

  const filterFeatures = (features: LandFeature[], values: FilterValues): LandFeature[] => {
    return features.filter((feature) => {
      const props = feature.properties;
      const address = props.address || "";
      const area = props.area || 0;

      const matchRegion = values.searchTerm === "" || address.includes(values.searchTerm);
      const matchArea = area >= values.minArea && area <= values.maxArea;

      let matchRent = true;
      if (values.isRentOnly) {
        const isAdmRentable = (props.adm_property || "").toLowerCase() === "o";
        const isGenRentable = (props.gen_property || "").startsWith("대부");
        matchRent = isAdmRentable || isGenRentable;
      }

      return matchRegion && matchArea && matchRent;
    });
  };

  const reset = (): void => {
    if (elements.regionSearchInput) {
      elements.regionSearchInput.value = "";
    }
    if (elements.minAreaInput) {
      elements.minAreaInput.value = "";
    }
    if (elements.maxAreaInput) {
      elements.maxAreaInput.value = "";
    }
    if (elements.rentOnlyFilter) {
      elements.rentOnlyFilter.checked = true;
    }
  };

  const attachEnter = (onEnter: () => void): void => {
    const attach = (input: HTMLInputElement | null): void => {
      if (!input) {
        return;
      }
      input.addEventListener("keydown", (event: KeyboardEvent) => {
        if (event.key === "Enter") {
          event.preventDefault();
          onEnter();
        }
      });
    };

    attach(elements.regionSearchInput);
    attach(elements.minAreaInput);
    attach(elements.maxAreaInput);
  };

  return {
    attachEnter,
    filterFeatures,
    getValues,
    reset
  };
}

export type Filters = ReturnType<typeof createFilters>;
