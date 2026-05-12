package jwt

import (
	jwtv5 "github.com/golang-jwt/jwt/v5"
)

type TokenType string

const (
	AccessToken  TokenType = "access"
	RefreshToken TokenType = "refresh"
)

type Claims struct {
	jwtv5.RegisteredClaims
	UserID int64     `json:"uid"`
	Role   string    `json:"role,omitempty"`
	Type   TokenType `json:"typ"`
}
