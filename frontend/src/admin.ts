import { createAdminCharts } from "./admin/charts";
import { requireElement } from "./admin/dom";
import { createGeomRefreshController } from "./admin/geom-refresh";
import { bindSettingsFormValidation } from "./admin/settings";
import { createAdminStatsController } from "./admin/stats";
import { initAdminTabs } from "./admin/tabs";
import { createAdminUploadActions } from "./admin/upload";

document.addEventListener("DOMContentLoaded", () => {
  const csrfInput = requireElement("csrfToken", HTMLInputElement);
  if (!csrfInput) {
    return;
  }

  const charts = createAdminCharts();
  const stats = createAdminStatsController(charts);
  const uploads = createAdminUploadActions(csrfInput.value);
  const geomRefresh = createGeomRefreshController(csrfInput.value, stats.load);

  initAdminTabs(() => {
    void stats.load(false);
  });
  uploads.bindUpload();
  uploads.bindPublicDownloadUpload();
  bindSettingsFormValidation();
  stats.bindRefreshButton();
  geomRefresh.bindRefreshButton();
});
