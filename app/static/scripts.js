document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');
    const userInfo = document.getElementById('user-info');

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const formData = new FormData(loginForm);
            const email = formData.get('email');
            const password = formData.get('password');

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        email: email,
                        password: password,
                    }),
                });

                if (response.ok) {
                    const data = await response.json();
                    const accessToken = data.access_token;
                    localStorage.setItem('access_token', accessToken);
                    window.location.href = '/'; // Перенаправление на главную страницу
                } else {
                    errorMessage.style.display = 'block';
                }
            } catch (error) {
                console.error('Login failed', error);
                errorMessage.style.display = 'block';
            }
        });
    }

    if (userInfo) {
        const token = localStorage.getItem('access_token');

        if (token) {
            fetch('/user-info', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.user) {
                    userInfo.textContent = `${data.user.first_name} ${data.user.last_name}`;
                } else {
                    userInfo.innerHTML = '<a href="/login" class="auth-button">Авторизация</a>';
                }
            })
            .catch(error => {
                console.error('Failed to fetch user info', error);
                userInfo.innerHTML = '<a href="/login" class="auth-button">Авторизация</a>';
            });
        } else {
            userInfo.innerHTML = '<a href="/login" class="auth-button">Авторизация</a>';
        }
    }
});
