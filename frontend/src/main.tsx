import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import GlobalStyles from "./design/GlobalStyles";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <GlobalStyles />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
