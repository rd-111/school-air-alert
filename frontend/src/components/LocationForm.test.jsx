import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LocationForm from "./LocationForm.jsx";
import en from "../i18n/en.json";

describe("location form", () => {
  it("reports coordinates outside valid ranges", () => {
    const onChange = vi.fn();
    render(<LocationForm location={{ latitude: 19, longitude: 72 }} onChange={onChange} labels={en} />);
    fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "91" } });
    fireEvent.click(screen.getByRole("button", { name: "Update location" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("submits valid coordinate numbers", () => {
    const onChange = vi.fn();
    render(<LocationForm location={{ latitude: 19, longitude: 72 }} onChange={onChange} labels={en} />);
    fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "40.5" } });
    fireEvent.change(screen.getByLabelText("Longitude"), { target: { value: "-73.25" } });
    fireEvent.click(screen.getByRole("button", { name: "Update location" }));
    expect(onChange).toHaveBeenCalledWith({ latitude: 40.5, longitude: -73.25 });
  });
});
