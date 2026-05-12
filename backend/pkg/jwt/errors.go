package jwt

import "errors"

var (
	ErrMissingToken   = errors.New("missing token")
	ErrTokenInvalid   = errors.New("invalid token")
	ErrTokenExpired   = errors.New("token expired")
	ErrWrongTokenType = errors.New("wrong token type")
)
