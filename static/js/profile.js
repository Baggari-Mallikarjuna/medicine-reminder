document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('profilePictureInput');
  const preview = document.getElementById('profilePreview');
  const fileError = document.getElementById('fileError');
  const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  const maxSize = 2 * 1024 * 1024; // 2MB

  if (!input) return;

  input.addEventListener('change', function (e) {
    const file = e.target.files[0];
    fileError.classList.add('d-none');
    fileError.textContent = '';
    if (!file) return;

    if (!allowed.includes(file.type)) {
      fileError.textContent = 'Invalid file type. Allowed: JPG, JPEG, PNG, WebP.';
      fileError.classList.remove('d-none');
      input.value = '';
      return;
    }

    if (file.size > maxSize) {
      fileError.textContent = 'File is too large. Max size is 2 MB.';
      fileError.classList.remove('d-none');
      input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = function (ev) {
      if (preview) preview.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });
});
