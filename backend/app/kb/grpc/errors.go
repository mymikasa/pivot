package grpc

import (
	"errors"
	"io"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/mymikasa/pivot/app/kb/domain"
)

func toGRPCError(err error) error {
	if err == nil {
		return nil
	}
	switch {
	case errors.Is(err, domain.ErrKBNotFound):
		return status.Error(codes.NotFound, "knowledge base not found")
	case errors.Is(err, domain.ErrDocNotFound):
		return status.Error(codes.NotFound, "document not found")
	case errors.Is(err, domain.ErrKBNameExists):
		return status.Error(codes.AlreadyExists, "knowledge base name already exists")
	case errors.Is(err, domain.ErrPermissionDenied):
		return status.Error(codes.PermissionDenied, "permission denied")
	case errors.Is(err, domain.ErrInvalidFileType):
		return status.Error(codes.InvalidArgument, "unsupported file type")
	case errors.Is(err, domain.ErrFileTooLarge):
		return status.Error(codes.InvalidArgument, "file exceeds 10MB limit")
	case errors.Is(err, domain.ErrUploadFailed):
		return status.Error(codes.Internal, "file upload failed")
	case errors.Is(err, io.EOF):
		return nil
	default:
		return status.Error(codes.Internal, "internal error")
	}
}
