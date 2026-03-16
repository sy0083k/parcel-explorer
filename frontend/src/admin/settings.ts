export function bindSettingsFormValidation(): void {
  const settingsForm = document.getElementById("settingsForm");
  if (!(settingsForm instanceof HTMLFormElement)) {
    return;
  }

  settingsForm.addEventListener("submit", (event) => {
    const input = document.querySelector<HTMLInputElement>('input[name="settings_password"]');
    if (input && input.value.trim()) {
      return;
    }

    alert("환경 변수 저장을 위해 관리자 비밀번호를 입력해주세요.");
    event.preventDefault();
  });
}
