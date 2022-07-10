var editDescMode = false;

var descText = document.getElementById('desc');
var editDescButton= document.getElementById('editDesc');
var editDescForm = document.getElementById('form');
editDescForm.style.display = 'none';

function toggleEditFontMode() {
    if (!editDescMode) {
        descText.style.display = 'none';
        editDescForm.style.display = 'block';
    }
    else {
        descText.style.display = 'block';
        editDescForm.style.display = 'none';
    }
    editDescMode = !editDescMode;
    editDescButton.disabled = editDescMode;
}