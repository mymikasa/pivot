package domain

import "errors"

var (
	ErrUserNotFound       = errors.New("user not found")
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrUserInactive       = errors.New("user inactive")
	ErrUnauthenticated    = errors.New("unauthenticated")
)
