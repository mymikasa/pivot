package ioc

import (
	"log/slog"
	"net/http"

	"google.golang.org/grpc"
)

type App struct {
	GRPC     *grpc.Server
	GRPCAddr string
	HTTP     *http.Server
	Logger   *slog.Logger
}

func NewApp(g *grpc.Server, h *http.Server, l *slog.Logger, c *Config) *App {
	return &App{
		GRPC:     g,
		GRPCAddr: c.GRPC.Addr,
		HTTP:     h,
		Logger:   l,
	}
}
