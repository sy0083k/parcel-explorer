import { describe, expect, test, vi } from "vitest";

import { createFilters } from "./filters";
import type { LandFeature } from "./types";

function createInput(value = ""): HTMLInputElement {
  const input = document.createElement("input");
  input.value = value;
  return input;
}

function createCheckbox(checked = false): HTMLInputElement {
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  return input;
}

const FEATURES: LandFeature[] = [
  { type: "Feature", geometry: null, properties: { address: "충남 서산시 대산읍", area: 120, adm_property: "O" } },
  { type: "Feature", geometry: null, properties: { address: "충남 서산시 예천동", area: 80, gen_property: "대부 가능" } },
  { type: "Feature", geometry: null, properties: { address: "충남 서산시 동문동", area: 500, adm_property: "X" } },
];

describe("createFilters", () => {
  test("reads current values with trim and numeric fallbacks", () => {
    const filters = createFilters({
      regionSearchInput: createInput(" 대산읍 "),
      minAreaInput: createInput("120"),
      maxAreaInput: createInput(""),
      rentOnlyFilter: createCheckbox(true),
    });

    expect(filters.getValues()).toEqual({
      isRentOnly: true,
      rawSearchTerm: " 대산읍 ",
      searchTerm: "대산읍",
      rawMinAreaInput: "120",
      rawMaxAreaInput: "",
      minArea: 120,
      maxArea: Number.POSITIVE_INFINITY,
    });
  });

  test("filters by region, area, and rent-only state", () => {
    const filters = createFilters({
      regionSearchInput: createInput(),
      minAreaInput: createInput(),
      maxAreaInput: createInput(),
      rentOnlyFilter: createCheckbox(),
    });

    const results = filters.filterFeatures(FEATURES, {
      isRentOnly: true,
      rawSearchTerm: "서산시",
      searchTerm: "서산시",
      rawMinAreaInput: "100",
      rawMaxAreaInput: "200",
      minArea: 100,
      maxArea: 200,
    });

    expect(results).toHaveLength(1);
    expect(results[0]?.properties.address).toContain("대산읍");
  });

  test("reset clears inputs and restores rent only checkbox", () => {
    const regionSearchInput = createInput("예천동");
    const minAreaInput = createInput("100");
    const maxAreaInput = createInput("500");
    const rentOnlyFilter = createCheckbox(false);
    const filters = createFilters({
      regionSearchInput,
      minAreaInput,
      maxAreaInput,
      rentOnlyFilter,
    });

    filters.reset();

    expect(regionSearchInput.value).toBe("");
    expect(minAreaInput.value).toBe("");
    expect(maxAreaInput.value).toBe("");
    expect(rentOnlyFilter.checked).toBe(true);
  });

  test("attachEnter triggers callback only for Enter key", () => {
    const onEnter = vi.fn();
    const regionSearchInput = createInput();
    const minAreaInput = createInput();
    const maxAreaInput = createInput();
    const filters = createFilters({
      regionSearchInput,
      minAreaInput,
      maxAreaInput,
      rentOnlyFilter: createCheckbox(),
    });

    filters.attachEnter(onEnter);

    regionSearchInput.dispatchEvent(new KeyboardEvent("keydown", { key: "a", bubbles: true }));
    minAreaInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    maxAreaInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    expect(onEnter).toHaveBeenCalledTimes(2);
  });
});
