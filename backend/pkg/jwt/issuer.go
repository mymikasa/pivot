package jwt

import (
	"strconv"
	"time"

	jwtv5 "github.com/golang-jwt/jwt/v5"
)

type Issuer struct {
	secret     []byte
	accessTTL  time.Duration
	refreshTTL time.Duration
	issuer     string
	audience   string
	now        func() time.Time
}

func NewIssuer(cfg Config) *Issuer {
	return &Issuer{
		secret:     []byte(cfg.Secret),
		accessTTL:  cfg.AccessTTL,
		refreshTTL: cfg.RefreshTTL,
		issuer:     cfg.Issuer,
		audience:   cfg.Audience,
		now:        time.Now,
	}
}

func (i *Issuer) Sign(userID int64, role string) (access, refresh string, err error) {
	access, err = i.signOne(userID, role, AccessToken, i.accessTTL)
	if err != nil {
		return "", "", err
	}
	refresh, err = i.signOne(userID, role, RefreshToken, i.refreshTTL)
	if err != nil {
		return "", "", err
	}
	return access, refresh, nil
}

func (i *Issuer) Refresh(refreshClaims *Claims) (string, error) {
	if refreshClaims.Type != RefreshToken {
		return "", ErrWrongTokenType
	}
	return i.signOne(refreshClaims.UserID, refreshClaims.Role, AccessToken, i.accessTTL)
}

func (i *Issuer) signOne(userID int64, role string, typ TokenType, ttl time.Duration) (string, error) {
	now := i.now()
	claims := Claims{
		RegisteredClaims: jwtv5.RegisteredClaims{
			Subject:   strconv.FormatInt(userID, 10),
			Issuer:    i.issuer,
			Audience:  jwtv5.ClaimStrings{i.audience},
			IssuedAt:  jwtv5.NewNumericDate(now),
			NotBefore: jwtv5.NewNumericDate(now),
			ExpiresAt: jwtv5.NewNumericDate(now.Add(ttl)),
		},
		UserID: userID,
		Role:   role,
		Type:   typ,
	}
	tok := jwtv5.NewWithClaims(jwtv5.SigningMethodHS256, claims)
	return tok.SignedString(i.secret)
}
