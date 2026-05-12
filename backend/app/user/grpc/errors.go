package grpc

import (
	"errors"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/mymikasa/pivot/app/user/domain"
)

func toGRPCError(err error) error {
	switch {
	case errors.Is(err, domain.ErrUserNotFound):
		return status.Error(codes.NotFound, "user not found")
	case errors.Is(err, domain.ErrInvalidCredentials):
		return status.Error(codes.Unauthenticated, "invalid credentials")
	case errors.Is(err, domain.ErrUserInactive):
		return status.Error(codes.PermissionDenied, "user inactive")
	case errors.Is(err, domain.ErrUnauthenticated):
		return status.Error(codes.Unauthenticated, "unauthenticated")
	default:
		return status.Error(codes.Internal, "internal error")
	}
}
