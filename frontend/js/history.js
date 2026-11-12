/**
 * Paginated Scan History view with filter and delete controls.
 */
function renderHistoryView(root) {
  let currentPage = 1;
  let currentFilter = "all";

  root.innerHTML = `
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem;">
      <div>
        <div class="page-eyebrow">Scan History</div>
        <h1 class="page-title">All Document Scans</h1>
        <p class="page-subtitle">Review or delete previous document verification results.</p>
      </div>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <button class="btn btn-primary btn-sm filter-btn" data-filter="all">All</button>
        <button class="btn btn-outline btn-sm filter-btn" data-filter="real">Genuine</button>
        <button class="btn btn-outline btn-sm filter-btn" data-filter="fake">Fake</button>
        <a href="#/scan" class="btn btn-primary btn-sm">New Scan</a>
      </div>
    </div>

    <div class="card">
      <div id="history-body">Loading scans...</div>
      <div id="history-pagination" style="display: flex; justify-content: center; gap: 0.5rem; margin-top: 1.25rem;"></div>
    </div>
  `;

  async function loadPage(page) {
    currentPage = page;
    const bodyEl = document.getElementById("history-body");
    const pagEl = document.getElementById("history-pagination");

    try {
      const data = await apiRequest(`/api/scans?page=${page}&per_page=10&filter=${currentFilter}`);
      if (!data.items.length) {
        bodyEl.innerHTML = `
          <div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
            No scan records found for this filter.
          </div>
        `;
        pagEl.innerHTML = "";
        return;
      }

      const rows = data.items
        .map((item, idx) => {
          const badgeCls = item.is_fake ? "badge-fake" : "badge-real";
          const badgeTxt = item.is_fake ? "Fake" : "Genuine";
          const dateTxt = item.scanned_at ? new Date(item.scanned_at).toLocaleString() : "—";
          const rowNum = (data.pagination.page - 1) * data.pagination.per_page + idx + 1;
          return `
            <tr data-scan-id="${item.id}">
              <td>${rowNum}</td>
              <td style="font-family: var(--mono); font-size: 0.82rem;">${escapeHtml(item.display_name)}</td>
              <td><span class="badge ${badgeCls}">${badgeTxt}</span></td>
              <td style="font-family: var(--mono);">${item.confidence}%</td>
              <td style="color: var(--text-muted); font-size: 0.82rem;">${escapeHtml(dateTxt)}</td>
              <td>
                <button class="btn btn-danger btn-sm delete-scan-btn" data-id="${item.id}">Delete</button>
              </td>
            </tr>
          `;
        })
        .join("");

      bodyEl.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Document</th>
                <th>Verdict</th>
                <th>Confidence</th>
                <th>Scanned At</th>
                <th></th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;

      bodyEl.querySelectorAll(".delete-scan-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("Delete this scan record?")) return;
          try {
            await apiRequest(`/api/scans/${btn.dataset.id}`, { method: "DELETE" });
            showToast("Scan deleted.", "success");
            loadPage(currentPage);
          } catch (err) {
            showToast(err.message, "error");
          }
        });
      });

      const p = data.pagination;
      pagEl.innerHTML = p.total_pages > 1 ? `
        <button class="btn btn-outline btn-sm" id="prev-page-btn" ${p.has_prev ? "" : "disabled"}>Prev</button>
        <span style="align-self: center; font-family: var(--mono); font-size: 0.82rem; color: var(--text-muted);">
          Page ${p.page} of ${p.total_pages}
        </span>
        <button class="btn btn-outline btn-sm" id="next-page-btn" ${p.has_next ? "" : "disabled"}>Next</button>
      ` : "";

      if (p.has_prev) {
        document.getElementById("prev-page-btn").addEventListener("click", () => loadPage(p.page - 1));
      }
      if (p.has_next) {
        document.getElementById("next-page-btn").addEventListener("click", () => loadPage(p.page + 1));
      }
    } catch (err) {
      bodyEl.innerHTML = `<div style="color: var(--danger);">${escapeHtml(err.message)}</div>`;
    }
  }

  root.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      root.querySelectorAll(".filter-btn").forEach((b) => {
        b.classList.remove("btn-primary");
        b.classList.add("btn-outline");
      });
      btn.classList.remove("btn-outline");
      btn.classList.add("btn-primary");
      currentFilter = btn.dataset.filter;
      loadPage(1);
    });
  });

  loadPage(1);
}
