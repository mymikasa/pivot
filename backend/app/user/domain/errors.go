package domain

import "errors"

var (
	ErrUserNotFound       = errors.New("user not found")
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrUserInactive       = errors.New("user inactive")
	ErrUnauthenticated    = errors.New("unauthenticated")
	ErrUserExists         = errors.New("user already exists")
	ErrRoleNotFound       = errors.New("role not found")
)
