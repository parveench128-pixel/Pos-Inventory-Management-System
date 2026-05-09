(function () {
    function initEmbeddedManageUsers(options) {
        const apiBase = options.apiBase || '/api';
        let selectedManagedUserId = null;
        let managedUsersCache = [];

            function formatManagedUserRole(role) {
                if (!role) return '';
                return role.charAt(0).toUpperCase() + role.slice(1);
            }

            function selectedManagedUser() {
                return managedUsersCache.find(u => u.id === selectedManagedUserId) || null;
            }

            function renderManageUsers() {
                const tbody = document.getElementById('usersManageTableBody');
                tbody.innerHTML = '';
                if (managedUsersCache.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No users found</td></tr>';
                    return;
                }

                managedUsersCache.forEach((user, index) => {
                    const selectedStyle = selectedManagedUserId === user.id ? ' style="background:#dce9ff;"' : '';
                    tbody.innerHTML += `
                        <tr${selectedStyle} onclick="selectManagedUser(${user.id})">
                            <td>${index + 1}</td>
                            <td>${user.username}</td>
                            <td>${user.active ? 'True' : 'False'}</td>
                            <td>${formatManagedUserRole(user.role)}</td>
                        </tr>`;
                });
                updateManagedPasswordText();
            }

            function updateManagedPasswordText() {
                const user = selectedManagedUser();
                const help = document.getElementById('managedPasswordHelp');
                if (!user) {
                    help.textContent = 'Select a user to reset password.';
                    return;
                }
                help.textContent = `To change the password for ${user.username}, click Reset Password.`;
            }

            function selectManagedUser(userId) {
                selectedManagedUserId = userId;
                renderManageUsers();
            }

            function loadManageUsers() {
                fetch(`${apiBase}/users`)
                    .then(r => r.json().then(data => ({ ok: r.ok, data })))
                    .then(({ ok, data }) => {
                        if (!ok) throw new Error(data.error || 'Failed to load users');
                        managedUsersCache = data;
                        if (selectedManagedUserId && !selectedManagedUser()) selectedManagedUserId = null;
                        renderManageUsers();
                    })
                    .catch(e => {
                        document.getElementById('usersManageTableBody').innerHTML = `<tr><td colspan="4" style="text-align:center;">${e.message}</td></tr>`;
                    });
            }

            function openAddUserModal() {
                document.getElementById('userForm').reset();
                document.getElementById('userModal').classList.add('active');
            }

            function closeUserModal() {
                document.getElementById('userModal').classList.remove('active');
            }

            function saveManagedUser(e) {
                e.preventDefault();
                const payload = {
                    username: document.getElementById('manageUserName').value.trim(),
                    password: document.getElementById('manageUserPassword').value,
                    role: document.getElementById('manageUserRole').value
                };
                fetch(`${apiBase}/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                    .then(r => r.json().then(data => ({ ok: r.ok, data })))
                    .then(({ ok, data }) => {
                        if (!ok) throw new Error(data.error || 'Could not create account');
                        closeUserModal();
                        loadManageUsers();
                        alert('Account created successfully');
                    })
                    .catch(e2 => alert('Error: ' + e2.message));
            }

            function updateManagedUser(userId, payload, successMessage) {
                fetch(`${apiBase}/users/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                    .then(r => r.json().then(data => ({ ok: r.ok, data })))
                    .then(({ ok, data }) => {
                        if (!ok) throw new Error(data.error || 'Update failed');
                        loadManageUsers();
                        alert(successMessage);
                    })
                    .catch(e => alert('Error: ' + e.message));
            }

            function changeManagedUserPassword() {
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                document.getElementById('changeCurrentPassword').value = '';
                document.getElementById('changeNewPassword').value = '';
                document.getElementById('changeRetypePassword').value = '';
                document.getElementById('changePasswordModal').classList.add('active');
            }

            function closeChangePasswordModal() {
                document.getElementById('changePasswordModal').classList.remove('active');
            }

            function saveChangedPassword(e) {
                e.preventDefault();
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                const currentPassword = document.getElementById('changeCurrentPassword').value;
                const newPassword = document.getElementById('changeNewPassword').value;
                const retypePassword = document.getElementById('changeRetypePassword').value;
                if (newPassword !== retypePassword) return alert('New password and re-type password do not match');

                fetch(`${apiBase}/users/${user.id}/change-password`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
                })
                    .then(r => r.json().then(data => ({ ok: r.ok, data })))
                    .then(({ ok, data }) => {
                        if (!ok) throw new Error(data.error || 'Could not change password');
                        closeChangePasswordModal();
                        alert('Password changed successfully');
                    })
                    .catch(e2 => alert('Error: ' + e2.message));
            }

            function openResetPasswordModal() {
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                document.getElementById('resetNewPassword').value = '';
                document.getElementById('resetRetypePassword').value = '';
                document.getElementById('resetPasswordModal').classList.add('active');
            }

            function closeResetPasswordModal() {
                document.getElementById('resetPasswordModal').classList.remove('active');
            }

            function saveResetPassword(e) {
                e.preventDefault();
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                const newPassword = document.getElementById('resetNewPassword').value;
                const retypePassword = document.getElementById('resetRetypePassword').value;
                if (newPassword !== retypePassword) return alert('New password and re-type password do not match');
                if (!newPassword) return;
                updateManagedUser(user.id, { password: newPassword }, 'Password reset successfully');
                closeResetPasswordModal();
            }

            function toggleManagedUserAccount() {
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                const nextActive = !user.active;
                updateManagedUser(user.id, { active: nextActive }, `Account ${nextActive ? 'activated' : 'deactivated'} successfully`);
            }

            function deleteManagedUser() {
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                if (!confirm(`Are you sure you want to remove ${user.username}?`)) return;

                fetch(`${apiBase}/users/${user.id}`, { method: 'DELETE' })
                    .then(r => {
                        if (r.ok) {
                            selectedManagedUserId = null;
                            loadManageUsers();
                            alert('User removed successfully');
                            return;
                        }
                        return r.json().then(err => Promise.reject(err));
                    })
                    .catch(e => alert('Error: ' + (e.error || 'Could not remove user')));
            }

            function showManagedUserProperties() {
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                document.getElementById('propertiesUsername').value = user.username;
                document.getElementById('propertiesActive').value = user.active ? 'true' : 'false';
                document.getElementById('propertiesModal').classList.add('active');
            }

            function closePropertiesModal() {
                document.getElementById('propertiesModal').classList.remove('active');
            }

            function saveManagedUserProperties(e) {
                e.preventDefault();
                const user = selectedManagedUser();
                if (!user) return alert('Please select a user first');
                const payload = {
                    username: document.getElementById('propertiesUsername').value.trim(),
                    active: document.getElementById('propertiesActive').value === 'true'
                };
                updateManagedUser(user.id, payload, 'User properties updated successfully');
                closePropertiesModal();
            }

        window.formatManagedUserRole = formatManagedUserRole;
        window.selectedManagedUser = selectedManagedUser;
        window.renderManageUsers = renderManageUsers;
        window.updateManagedPasswordText = updateManagedPasswordText;
        window.selectManagedUser = selectManagedUser;
        window.loadManageUsers = loadManageUsers;
        window.openAddUserModal = openAddUserModal;
        window.closeUserModal = closeUserModal;
        window.saveManagedUser = saveManagedUser;
        window.updateManagedUser = updateManagedUser;
        window.changeManagedUserPassword = changeManagedUserPassword;
        window.closeChangePasswordModal = closeChangePasswordModal;
        window.saveChangedPassword = saveChangedPassword;
        window.openResetPasswordModal = openResetPasswordModal;
        window.closeResetPasswordModal = closeResetPasswordModal;
        window.saveResetPassword = saveResetPassword;
        window.toggleManagedUserAccount = toggleManagedUserAccount;
        window.deleteManagedUser = deleteManagedUser;
        window.showManagedUserProperties = showManagedUserProperties;
        window.closePropertiesModal = closePropertiesModal;
        window.saveManagedUserProperties = saveManagedUserProperties;
    }

    window.initEmbeddedManageUsers = initEmbeddedManageUsers;
})();
