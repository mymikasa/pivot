package ioc

import (
	"log/slog"
	"os"
	"strings"
)

func InitLogger(c *Config) *slog.Logger {
	var level slog.Level
	switch strings.ToUpper(c.Log.Level) {
	case "DEBUG":
		level = slog.LevelDebug
	case "WARN", "WARNING":
		level = slog.LevelWarn
	case "ERROR":
		level = slog.LevelError
	default:
		level = slog.LevelInfo
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: level}))
}
