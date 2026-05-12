package ioc

import (
	"context"
	"net/http"

	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/encoding/protojson"

	userv1 "github.com/mymikasa/pivot/api/gen/user/v1"
)

func InitHTTPGateway(c *Config) (*http.Server, error) {
	mux := runtime.NewServeMux(
		runtime.WithMarshalerOption(runtime.MIMEWildcard, &runtime.JSONPb{
			MarshalOptions: protojson.MarshalOptions{
				UseProtoNames:   true, // snake_case 字段，与前端契约一致
				EmitUnpopulated: true, // 空值也下发，前端 ts 类型才不丢字段
			},
			UnmarshalOptions: protojson.UnmarshalOptions{
				DiscardUnknown: true,
			},
		}),
	)
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
