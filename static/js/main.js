// ── Sidebar Toggle ────────────────────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('sidebar-toggle');
const overlay = document.getElementById('sidebar-overlay');

if (toggleBtn) {
  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  });
}

if (overlay) {
  overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  });
}

// ── Auto-show Bootstrap Toasts ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const toastEls = document.querySelectorAll('.toast');
  toastEls.forEach(el => {
    const toast = new bootstrap.Toast(el, { delay: 4000 });
    toast.show();
  });
});

// ── Form Submit Spinner ───────────────────────────────────────────────────────
document.querySelectorAll('form[data-loading]').forEach(form => {
  form.addEventListener('submit', function () {
    const btn = this.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      const originalHTML = btn.innerHTML;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> Processing...`;
      // Re-enable after 8s as fallback
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
      }, 8000);
    }
  });
});

// ── Confirm Delete Modal ──────────────────────────────────────────────────────
const confirmModal = document.getElementById('confirmModal');
if (confirmModal) {
  confirmModal.addEventListener('show.bs.modal', function (event) {
    const trigger = event.relatedTarget;
    const action = trigger.getAttribute('data-action');
    const label = trigger.getAttribute('data-label') || 'this item';
    const bodyEl = this.querySelector('#confirmModalBody');
    const formEl = this.querySelector('#confirmModalForm');

    if (bodyEl) bodyEl.textContent = `Are you sure you want to delete "${label}"? This action cannot be undone.`;
    if (formEl && action) formEl.setAttribute('action', action);
  });
}

// ── Approve/Reject Confirm Modal ──────────────────────────────────────────────
const actionModal = document.getElementById('actionModal');
if (actionModal) {
  actionModal.addEventListener('show.bs.modal', function (event) {
    const trigger = event.relatedTarget;
    const action = trigger.getAttribute('data-action');
    const type = trigger.getAttribute('data-type'); // 'approve' or 'reject'
    const label = trigger.getAttribute('data-label') || 'this request';
    const bodyEl = this.querySelector('#actionModalBody');
    const formEl = this.querySelector('#actionModalForm');
    const titleEl = this.querySelector('#actionModalTitle');
    const btnEl = this.querySelector('#actionModalBtn');

    if (type === 'approve') {
      if (titleEl) titleEl.textContent = 'Approve Request';
      if (bodyEl) bodyEl.textContent = `Approve adoption request for "${label}"? The pet will be marked as adopted.`;
      if (btnEl) { btnEl.textContent = 'Approve'; btnEl.className = 'btn btn-success'; }
    } else {
      if (titleEl) titleEl.textContent = 'Reject Request';
      if (bodyEl) bodyEl.textContent = `Reject adoption request for "${label}"? The pet will remain available.`;
      if (btnEl) { btnEl.textContent = 'Reject'; btnEl.className = 'btn btn-danger'; }
    }

    if (formEl && action) formEl.setAttribute('action', action);
  });
}

// ── Search with debounce ──────────────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');
if (searchInput) {
  let debounceTimer;
  searchInput.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const form = this.closest('form');
      if (form) form.submit();
    }, 400);
  });
}
