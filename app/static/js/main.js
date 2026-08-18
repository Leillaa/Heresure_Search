// [EN] The "Send Email" button is still a stub — it only shows a toast.
// Loaded as a classic script (NOT type="module") because the button uses an
// inline onclick="notReady(this)", which resolves against the global scope.
// [RU] Кнопка "Отправить письмо" пока заглушка — только показывает toast.
// Подключается как обычный скрипт (НЕ type="module"), потому что кнопка
// использует инлайновый onclick="notReady(this)", который ищет функцию в
// глобальной области видимости.
function notReady(btn) {
  const toast = document.getElementById('toast');
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 1500);
}
