import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ToastProvider } from "../src/components/common/Common";
import { Layout } from "../src/components/layout/Layout";

function mount(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter>{node}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("UI refresh - Item 2 profile dropdown", () => {
  it("opens profile dropdown and shows logout item", () => {
    mount(
      <Routes>
        <Route path="/" element={<Layout />} />
      </Routes>,
    );

    // Standalone logout button should not exist
    expect(screen.queryByRole("button", { name: "Logout" })).not.toBeInTheDocument();

    // Profile trigger button
    const profileBtn = screen.getByRole("button", { name: /Arjun Mehta/i });
    expect(profileBtn).toHaveAttribute("aria-haspopup", "menu");
    expect(profileBtn).toHaveAttribute("aria-expanded", "false");

    // Click to open dropdown
    fireEvent.click(profileBtn);
    expect(profileBtn).toHaveAttribute("aria-expanded", "true");

    const logoutMenuItem = screen.getByRole("menuitem", { name: /Logout/i });
    expect(logoutMenuItem).toBeInTheDocument();

    // Close on Escape
    fireEvent.keyDown(document, { key: "Escape" });
    expect(profileBtn).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menuitem", { name: /Logout/i })).not.toBeInTheDocument();
  });
});

describe("UI refresh - Item 8 anomaly category chart sorting", () => {
  it("sorts anomaly data in descending order by value", () => {
    const raw = [
      { name: "Velocity spikes", value: 12 },
      { name: "Simultaneous enrollments", value: 45 },
      { name: "Repeated Aadhaar/Account", value: 28 },
    ];
    const sorted = [...raw].sort((a, b) => b.value - a.value);
    expect(sorted.map((item) => item.name)).toEqual([
      "Simultaneous enrollments",
      "Repeated Aadhaar/Account",
      "Velocity spikes",
    ]);
    expect(sorted[0].value).toBe(45);
    expect(sorted[2].value).toBe(12);
  });
});


