import { KeyRound } from "lucide-react";
import { useState } from "react";
import { Navigate, Outlet, useNavigate } from "react-router-dom";
import { Panel } from "../../components/common/Common";

export function Protected() {
  return sessionStorage.getItem("grantlens.demo-session") === "active" ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace />
  );
}

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  return (
    <main className="login-page">
      <div className="login-brand">
        <h1>SATARKK</h1>
        <p>Scholarship Forensic Intelligence</p>
        <div className="tricolor" />
      </div>
      <Panel title="Auditor demo access">
        <form
          className="settings-body"
          onSubmit={(e) => {
            e.preventDefault();
            if (
              email.trim().toLowerCase() !== "auditor@grantlens.demo" ||
              password !== "GrantLens123"
            ) {
              setError("The demo email or password is incorrect.");
              return;
            }
            sessionStorage.setItem("grantlens.demo-session", "active");
            navigate("/", { replace: true });
          }}
        >
          <div className="demo-credentials-box">
            <div className="demo-credentials-header">
              <span className="demo-credentials-badge">
                <KeyRound size={13} /> Demo Credentials
              </span>
              <button
                type="button"
                className="demo-autofill-btn"
                onClick={() => {
                  setEmail("auditor@grantlens.demo");
                  setPassword("GrantLens123");
                  setError("");
                }}
              >
                Auto-fill
              </button>
            </div>
            <div className="demo-credential-row">
              <span className="demo-cred-label">Email:</span>
              <code className="demo-cred-val">auditor@grantlens.demo</code>
            </div>
            <div className="demo-credential-row">
              <span className="demo-cred-label">Password:</span>
              <code className="demo-cred-val">GrantLens123</code>
            </div>
          </div>

          <label>
            Email
            <input
              required
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              required
              type={show ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label className="show-pw-label">
            <input
              type="checkbox"
              checked={show}
              onChange={(e) => setShow(e.target.checked)}
            />{" "}
            Show password
          </label>
          {error && <p role="alert">{error}</p>}
          <button className="primary" type="submit">
            Sign in
          </button>
          <small>
            Frontend demonstration access only. API endpoints are not
            authenticated. No government affiliation.
          </small>
        </form>
      </Panel>
    </main>
  );
}
