package main

import (
	"context"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	app, cleanup, err := initApp()
	if err != nil {
		slog.Error("init app", slog.Any("err", err))
		os.Exit(1)
	}
	defer cleanup()

	lis, err := net.Listen("tcp", app.GRPCAddr)
	if err != nil {
		app.Logger.Error("listen", slog.Any("err", err))
		os.Exit(1)
	}
	go func() {
		app.Logger.Info("grpc listening", slog.String("addr", app.GRPCAddr))
		if err := app.GRPC.Serve(lis); err != nil {
			app.Logger.Error("grpc serve", slog.Any("err", err))
		}
	}()

	go func() {
		app.Logger.Info("http listening", slog.String("addr", app.HTTP.Addr))
		if err := app.HTTP.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			app.Logger.Error("http serve", slog.Any("err", err))
		}
	}()

	<-ctx.Done()
	app.Logger.Info("shutting down")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = app.HTTP.Shutdown(shutdownCtx)
	app.GRPC.GracefulStop()
}
