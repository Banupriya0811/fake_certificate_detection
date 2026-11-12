/**
 * Authentication views: Login and Register.
 */
function renderLoginView(root) {
  root.innerHTML = `
    <div class="card auth-card">
      <div class="page-eyebrow">Authentication</div>
      <h1 class="page-title" style="margin-bottom: 0.35rem;">Sign in to DocVerify AI</h1>
      <p class="page-subtitle" style="margin-bottom: 1.5rem;">Verify marksheets and certificates with AI.</p>

      <form id="login-form">
        <div class="form-group">
          <label for="login-username">Username</label>
          <input id="login-username" type="text" required autocomplete="username" />
        </div>
        <div class="form-group">
          <label for="login-password">Password</label>
          <input id="login-password" type="password" required autocomplete="current-password" />
        </div>
        <button class="btn btn-primary" style="width: 100%;" type="submit">Sign In</button>
      </form>

      <div class="auth-switch">
        New here? <a href="#/register">Create an account</a>
      </div>
    </div>
  `;

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type='submit']");
    btn.disabled = true;
    try {
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: document.getElementById("login-username").value.trim(),
          password: document.getElementById("login-password").value,
        }),
      });
      setAuthSession(data.token, data.user);
      showToast(`Welcome back, ${data.user.username}!`, "success");
      window.location.hash = "#/scan";
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

function renderRegisterView(root) {
  root.innerHTML = `
    <div class="card auth-card">
      <div class="page-eyebrow">Create Account</div>
      <h1 class="page-title" style="margin-bottom: 0.35rem;">Register</h1>
      <p class="page-subtitle" style="margin-bottom: 1.5rem;">Create your DocVerify AI workspace account.</p>

      <form id="register-form">
        <div class="form-group">
          <label for="reg-username">Username</label>
          <input id="reg-username" type="text" required maxlength="100" />
        </div>
        <div class="form-group">
          <label for="reg-email">Email Address</label>
          <input id="reg-email" type="email" required />
        </div>
        <div class="form-group">
          <label for="reg-password">Password (min 6 chars)</label>
          <input id="reg-password" type="password" required minlength="6" />
        </div>
        <button class="btn btn-primary" style="width: 100%;" type="submit">Create Account</button>
      </form>

      <div class="auth-switch">
        Already have an account? <a href="#/login">Sign in</a>
      </div>
    </div>
  `;

  document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type='submit']");
    btn.disabled = true;
    try {
      const data = await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: document.getElementById("reg-username").value.trim(),
          email: document.getElementById("reg-email").value.trim(),
          password: document.getElementById("reg-password").value,
        }),
      });
      setAuthSession(data.token, data.user);
      showToast("Account created!", "success");
      window.location.hash = "#/scan";
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

