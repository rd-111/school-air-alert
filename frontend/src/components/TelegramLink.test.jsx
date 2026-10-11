import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TelegramLink from "./TelegramLink.jsx";

const labels = {
  telegramBotLink: "Open Telegram bot",
  telegramBotUnavailable: "Telegram bot is not configured.",
};

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

describe("TelegramLink", () => {
  it("shows a safe public bot link when a username is configured", () => {
    vi.stubEnv("VITE_TELEGRAM_BOT_USERNAME", "schoolalert11_bot");
    render(<TelegramLink labels={labels} />);

    expect(screen.getByRole("link", { name: labels.telegramBotLink })).toHaveAttribute(
      "href",
      "https://t.me/schoolalert11_bot",
    );
  });

  it("does not create a link for an invalid username", () => {
    vi.stubEnv("VITE_TELEGRAM_BOT_USERNAME", "not/a/bot");
    render(<TelegramLink labels={labels} />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(labels.telegramBotUnavailable)).toBeInTheDocument();
  });
});
