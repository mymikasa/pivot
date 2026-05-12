package ioc

import (
	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
)

func InitJWTIssuer(c *Config) *jwtpkg.Issuer {
	return jwtpkg.NewIssuer(c.JWT)
}

func InitJWTVerifier(c *Config) *jwtpkg.Verifier {
	return jwtpkg.NewVerifier(c.JWT)
}
