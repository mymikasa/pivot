package jwt

import "context"

type ctxKey int

const claimsKey ctxKey = 0

func WithClaims(ctx context.Context, c *Claims) context.Context {
	return context.WithValue(ctx, claimsKey, c)
}

func ClaimsFromContext(ctx context.Context) (*Claims, bool) {
	c, ok := ctx.Value(claimsKey).(*Claims)
	return c, ok
}

func UserIDFromContext(ctx context.Context) (int64, bool) {
	c, ok := ClaimsFromContext(ctx)
	if !ok {
		return 0, false
	}
	return c.UserID, true
}

func RoleFromContext(ctx context.Context) (string, bool) {
	c, ok := ClaimsFromContext(ctx)
	if !ok {
		return "", false
	}
	return c.Role, true
}
