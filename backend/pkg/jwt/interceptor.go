package jwt

import (
	"context"
	"strings"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

const (
	mdAuthorization = "authorization"
	bearerScheme    = "bearer "
)

func UnaryAuth(v *Verifier, whitelist map[string]struct{}) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (any, error) {
		if _, ok := whitelist[info.FullMethod]; ok {
			return handler(ctx, req)
		}
		claims, err := authorize(ctx, v)
		if err != nil {
			return nil, err
		}
		return handler(WithClaims(ctx, claims), req)
	}
}

func StreamAuth(v *Verifier, whitelist map[string]struct{}) grpc.StreamServerInterceptor {
	return func(srv any, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		if _, ok := whitelist[info.FullMethod]; ok {
			return handler(srv, ss)
		}
		claims, err := authorize(ss.Context(), v)
		if err != nil {
			return err
		}
		wrapped := &wrappedStream{ServerStream: ss, ctx: WithClaims(ss.Context(), claims)}
		return handler(srv, wrapped)
	}
}

func authorize(ctx context.Context, v *Verifier) (*Claims, error) {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return nil, status.Error(codes.Unauthenticated, "unauthenticated")
	}
	vals := md.Get(mdAuthorization)
	if len(vals) == 0 {
		return nil, status.Error(codes.Unauthenticated, "unauthenticated")
	}
	raw := vals[0]
	if !strings.HasPrefix(strings.ToLower(raw), bearerScheme) {
		return nil, status.Error(codes.Unauthenticated, "unauthenticated")
	}
	token := strings.TrimSpace(raw[len(bearerScheme):])
	claims, err := v.Parse(token)
	if err != nil {
		return nil, status.Error(codes.Unauthenticated, "unauthenticated")
	}
	if claims.Type != AccessToken {
		return nil, status.Error(codes.Unauthenticated, "unauthenticated")
	}
	return claims, nil
}

type wrappedStream struct {
	grpc.ServerStream
	ctx context.Context
}

func (w *wrappedStream) Context() context.Context { return w.ctx }
