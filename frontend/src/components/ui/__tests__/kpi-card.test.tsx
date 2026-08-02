import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { KPICard } from "../kpi-card";

describe("KPICard", () => {
  it("renders the title and formatted value", () => {
    render(<KPICard title="Total Revenue" value="R$ 15.84M" />);
    expect(screen.getByText("Total Revenue")).toBeInTheDocument();
    expect(screen.getByText("R$ 15.84M")).toBeInTheDocument();
  });

  it("shows the change badge when change is provided", () => {
    render(<KPICard title="Orders" value="98,666" change={4.2} trend="up" />);
    expect(screen.getByText("4.2%")).toBeInTheDocument();
    expect(screen.getByText("vs last period")).toBeInTheDocument();
  });

  it("omits the change badge when change is null", () => {
    const { container } = render(<KPICard title="Orders" value="98,666" change={null} />);
    expect(screen.queryByText("vs last period")).not.toBeInTheDocument();
    expect(container.querySelector("h2")?.textContent).toBe("98,666");
  });
});
