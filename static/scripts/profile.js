var editBioMode = false;

var bioText = document.getElementById('bio');
var editBioButton= document.getElementById('editBio');
var editBioForm = document.getElementById('form');
editBioForm.style.display = 'none';

function toggleEditBioMode() {
    if (!editBioMode) {
        bioText.style.display = 'none';
        editBioForm.style.display = 'block';
    }
    else {
        bioText.style.display = 'block';
        editBioForm.style.display = 'none';
    }
    editBioMode = !editBioMode;
    editBioButton.disabled = editBioMode;
}