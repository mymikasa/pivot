package domain

import "errors"

var (
	ErrKBNotFound         = errors.New("knowledge base not found")
	ErrKBNameExists       = errors.New("knowledge base name already exists")
	ErrDocNotFound        = errors.New("document not found")
	ErrPermissionDenied   = errors.New("permission denied")
	ErrInvalidFileType    = errors.New("unsupported file type")
	ErrFileTooLarge       = errors.New("file exceeds 100MB limit")
	ErrUploadFailed       = errors.New("file upload failed")
	ErrUploadNotConfirmed = errors.New("upload not yet confirmed")
)
