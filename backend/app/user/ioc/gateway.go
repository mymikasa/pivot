package ioc

import (
	"context"
	"net/http"

	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	userv1 "github.com/mymikasa/pivot/api/gen/user/v1"
)

func InitHTTPGateway(c *Config) (*http.Server, error) {
	mux := runtime.NewServeMux()
	opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}

	if err := userv1.RegisterUserServiceHandlerFromEndpoint(
		context.Background(), mux, c.GRPC.Addr, opts,
	); err != nil {
		return nil, err
	}
	return &http.Server{
		Addr:    c.HTTP.Addr,
		Handler: mux,
	}, nil
}
