async function postBookmarkToggle(dishId) {
  const csrfToken = document.getElementById('csrfToken').value;
  const response = await fetch(`/dish/${dishId}/bookmark`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.success) {
    alert(data.error || 'ブックマークの更新に失敗しました');
    return null;
  }
  return data;
}

function updateBookmarkBadge(count) {
  const badge = document.getElementById('bookmarkBadge');
  if (!badge) return;
  if (count > 0) {
    badge.textContent = count;
    badge.style.display = '';
  } else {
    badge.style.display = 'none';
  }
}

async function toggleBookmark(dishId, btnEl) {
  const data = await postBookmarkToggle(dishId);
  if (!data) return;

  const icon = btnEl.querySelector('i');
  btnEl.classList.toggle('bookmarked', data.bookmarked);
  icon.className = data.bookmarked ? 'bi bi-bookmark-fill' : 'bi bi-bookmark';
  updateBookmarkBadge(data.bookmark_count);
}

function renderBookmarkDropdownMessage(menu, text, className) {
  menu.innerHTML = '';
  const li = document.createElement('li');
  li.className = className;
  li.textContent = text;
  menu.appendChild(li);
}

async function loadBookmarkDropdown() {
  const menu = document.getElementById('bookmarkDropdownMenu');
  if (!menu) return;
  renderBookmarkDropdownMessage(menu, '読み込み中...', 'px-3 py-2 text-muted small');

  try {
    const response = await fetch('/bookmarks');
    const bookmarks = await response.json();

    if (!bookmarks.length) {
      renderBookmarkDropdownMessage(menu, 'ブックマークはまだありません', 'px-3 py-2 text-muted small');
      return;
    }

    menu.innerHTML = '';
    bookmarks.forEach(b => {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.className = 'dropdown-item bookmark-dropdown-item';
      link.href = b.url;

      const nameDiv = document.createElement('div');
      nameDiv.textContent = b.dish_name;

      const dateDiv = document.createElement('div');
      dateDiv.className = 'text-muted small';
      dateDiv.textContent = `${b.created_at} 登録`;

      link.appendChild(nameDiv);
      link.appendChild(dateDiv);
      li.appendChild(link);
      menu.appendChild(li);
    });
  } catch (error) {
    renderBookmarkDropdownMessage(menu, '読み込みに失敗しました', 'px-3 py-2 text-danger small');
  }
}
