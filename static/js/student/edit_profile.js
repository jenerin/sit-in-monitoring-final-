/* ═══════════════════════════════════════════════════════════
   student/edit_profile.js  —  Photo upload preview
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const photoInput    = document.getElementById('photoInput');
  const avatarPreview = document.getElementById('avatarPreview');
  const avatarInitials= document.getElementById('avatarInitials');

  if (!photoInput) return;

  photoInput.addEventListener('change', () => {
    const file = photoInput.files[0];
    if (!file) return;

    // Validate type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file (PNG, JPG, GIF, WEBP).');
      photoInput.value = '';
      return;
    }

    // Validate size (max 5 MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be smaller than 5 MB.');
      photoInput.value = '';
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      if (avatarPreview) {
        avatarPreview.src = e.target.result;
        avatarPreview.style.display = 'block';
      }
      if (avatarInitials) {
        avatarInitials.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  });
});
