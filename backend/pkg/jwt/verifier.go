package jwt

import (
	"errors"
	"time"

	jwtv5 "github.com/golang-jwt/jwt/v5"
)

type Verifier struct {
	secret   []byte
	issuer   string
	audience string
	now      func() time.Time
}

func NewVerifier(cfg Config) *Verifier {
	return &Verifier{
		secret:   []byte(cfg.Secret),
		issuer:   cfg.Issuer,
		audience: cfg.Audience,
		now:      time.Now,
	}
}

func (v *Verifier) Parse(token string) (*Claims, error) {
	claims := &Claims{}
	parser := jwtv5.NewParser(
		jwtv5.WithValidMethods([]string{jwtv5.SigningMethodHS256.Alg()}),
		jwtv5.WithIssuer(v.issuer),
		jwtv5.WithAudience(v.audience),
		jwtv5.WithExpirationRequired(),
		jwtv5.WithTimeFunc(v.now),
	)
	parsed, err := parser.ParseWithClaims(token, claims, func(t *jwtv5.Token) (any, error) {
		return v.secret, nil
	})
	if err != nil {
		switch {
		case errors.Is(err, jwtv5.ErrTokenExpired):
			return nil, ErrTokenExpired
		default:
			return nil, ErrTokenInvalid
		}
	}
	if !parsed.Valid {
		return nil, ErrTokenInvalid
	}
	return claims, nil
}
