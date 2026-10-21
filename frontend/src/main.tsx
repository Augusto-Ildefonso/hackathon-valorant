import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { FiltersProvider } from "./lib/filters";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: false } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <FiltersProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </FiltersProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
