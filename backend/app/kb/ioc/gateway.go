package ioc

import (
	"context"
	"net/http"

	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/encoding/protojson"

	kbv1 "github.com/mymikasa/pivot/api/gen/kb/v1"
)

func InitHTTPGateway(c *Config) (*http.Server, error) {
	mux := runtime.NewServeMux(
		runtime.WithMarshalerOption(runtime.MIMEWildcard, &runtime.JSONPb{
			MarshalOptions: protojson.MarshalOptions{
				UseProtoNames:   true,
				EmitUnpopulated: true,
			},
			UnmarshalOptions: protojson.UnmarshalOptions{
				DiscardUnknown: true,
			},
		}),
	)
	opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}

	if err := kbv1.RegisterKnowledgeBaseServiceHandlerFromEndpoint(
		context.Background(), mux, c.GRPC.Addr, opts,
	); err != nil {
		return nil, err
	}
	return &http.Server{
		Addr:    c.HTTP.Addr,
		Handler: mux,
	}, nil
}
