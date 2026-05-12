package ioc

import (
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	userv1 "github.com/mymikasa/pivot/api/gen/user/v1"
	usergrpc "github.com/mymikasa/pivot/app/user/grpc"
	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
)

var authWhitelist = map[string]struct{}{
	"/pivot.user.v1.UserService/Register":                            {},
	"/pivot.user.v1.UserService/Login":                               {},
	"/pivot.user.v1.UserService/RefreshToken":                        {},
	"/grpc.reflection.v1.ServerReflection/ServerReflectionInfo":      {},
	"/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo": {},
}

func InitGRPCServer(svc *usergrpc.UserServer, v *jwtpkg.Verifier) *grpc.Server {
	s := grpc.NewServer(
		grpc.UnaryInterceptor(jwtpkg.UnaryAuth(v, authWhitelist)),
		grpc.StreamInterceptor(jwtpkg.StreamAuth(v, authWhitelist)),
	)
	userv1.RegisterUserServiceServer(s, svc)
	reflection.Register(s)
	return s
}
