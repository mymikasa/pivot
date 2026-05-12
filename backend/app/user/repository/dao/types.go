package dao

import "context"

type DAO interface {
	FindAll(ctx context.Context) ([]User, error)
	FindByUsername(ctx context.Context, username string) (User, error)
}
