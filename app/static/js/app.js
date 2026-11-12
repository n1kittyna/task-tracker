// 1) Подтверждение удаления: работает без Bootstrap-модалок.
document.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-confirm]");
  if (form && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
});

// 2) Опционально: смена статуса через fetch, без перезагрузки страницы.
//    Без JS форма отправится обычным POST — прогрессивное улучшение.
document.addEventListener("change", async (event) => {
  const select = event.target.closest("select[data-status-url]");
  if (!select) return;

  const token = document.querySelector('meta[name="csrf-token"]').content;
  try {
    const response = await fetch(select.dataset.statusUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ status: select.value }),
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    const badge = document.querySelector("[data-status-badge]");
    if (badge) {
      badge.textContent = data.status_label;
      badge.className = "badge " + {
        todo: "bg-secondary", in_progress: "bg-primary", done: "bg-success"
      }[data.status];
    }
  } catch (e) {
    alert("Не удалось обновить статус: " + e.message);
  }
});