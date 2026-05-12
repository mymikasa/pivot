package ioc

import (
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	kbv1 "github.com/mymikasa/pivot/api/gen/kb/v1"
	kbgrpc "github.com/mymikasa/pivot/app/kb/grpc"
	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
)

var authWhitelist = map[string]struct{}{
	"/grpc.reflection.v1.ServerReflection/ServerReflectionInfo":      {},
	"/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo": {},
}

func InitGRPCServer(svc *kbgrpc.KbServer, v *jwtpkg.Verifier) *grpc.Server {
	s := grpc.NewServer(
		grpc.UnaryInterceptor(jwtpkg.UnaryAuth(v, authWhitelist)),
		grpc.StreamInterceptor(jwtpkg.StreamAuth(v, authWhitelist)),
	)
	kbv1.RegisterKnowledgeBaseServiceServer(s, svc)
	reflection.Register(s)
	return s
}
