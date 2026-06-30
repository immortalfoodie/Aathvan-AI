import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function GoogleCallbackPage() {
  const [searchParams] = useSearchParams();
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const err = searchParams.get("error");

    if (err) {
      setErrorMsg(err);
    } else if (token) {
      loginWithToken(token)
        .then(() => {
          navigate("/");
        })
        .catch((e) => {
          setErrorMsg("Failed to authenticate session. Please try again.");
        });
    } else {
      setErrorMsg("Invalid redirect callback. No tokens found.");
    }
  }, [searchParams, loginWithToken, navigate]);

  if (errorMsg) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-bg)] p-4 text-center">
        <div className="card max-w-md w-full p-8 border border-[var(--color-danger)] shadow-lg">
          <span className="text-4xl mb-4">⚠️</span>
          <h2 className="text-xl font-bold text-[var(--color-danger)] mb-2">Google Auth Error</h2>
          <p className="text-[var(--color-text-secondary)] mb-6 text-sm leading-relaxed">{errorMsg}</p>
          <button className="btn btn-primary w-full" onClick={() => navigate("/login")}>
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-bg)] p-4">
      <div className="text-center">
        <div className="loading-spinner mb-4"></div>
        <p className="text-[var(--color-text-secondary)] font-medium">Securing session via Google...</p>
      </div>
    </div>
  );
}
