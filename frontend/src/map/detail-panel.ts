import type { LandFeatureProperties } from "./types";

type PanelElements = {
  panel: HTMLElement;
  content: HTMLElement;
  closeBtn: HTMLElement;
};

export function createDetailPanel(elements: PanelElements) {
  const show = (): void => {
    elements.panel.classList.remove("is-hidden");
  };

  const dismiss = (): void => {
    elements.panel.classList.add("is-hidden");
  };

  const clear = (): void => {
    const empty = document.createElement("div");
    empty.className = "land-info-empty";
    empty.textContent = "토지를 선택하면 상세 정보가 표시됩니다.";
    elements.content.replaceChildren(empty);
  };

  const normalize = (v: unknown): string =>
    String(v ?? "")
      .replace(/[\r\n\t]+/g, " ")
      .trim();

  const renderProperties = (props: LandFeatureProperties): void => {
    const rows: { label: string; value: string }[] =
      props.source_fields && props.source_fields.length > 0
        ? props.source_fields
            .map((f) => ({ label: f.label, value: normalize(f.value) }))
            .filter((r) => r.value !== "")
        : [
            { label: "주소", value: normalize(props.address) },
            { label: "면적", value: props.area != null ? `${props.area}㎡` : "" },
            { label: "지목", value: normalize(props.land_type) },
            { label: "행정재산", value: normalize(props.adm_property) },
            { label: "일반재산", value: normalize(props.gen_property) },
            { label: "문의", value: normalize(props.contact) },
          ].filter((r) => r.value !== "");

    const dl = document.createElement("dl");
    dl.className = "land-info-grid";
    for (const { label, value } of rows) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    elements.content.replaceChildren(dl);
  };

  const bindCloseButton = (onClose: () => void): void => {
    elements.closeBtn.addEventListener("click", onClose);
  };

  // 초기 empty state
  clear();

  return { show, dismiss, clear, renderProperties, bindCloseButton };
}

export type DetailPanel = ReturnType<typeof createDetailPanel>;
