export default function TelegramLink({ labels }) {
  const username = import.meta.env.VITE_TELEGRAM_BOT_USERNAME || "";
  const validUsername = /^[A-Za-z0-9_]{5,32}$/.test(username);

  return (
    <p className="telegram-link">
      {validUsername ? (
        <a href={`https://t.me/${username}`} target="_blank" rel="noreferrer">
          {labels.telegramBotLink}
        </a>
      ) : labels.telegramBotUnavailable}
    </p>
  );
}
