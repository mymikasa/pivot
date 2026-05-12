package dao

import "context"

type DAO interface {
	FindAll(ctx context.Context) ([]User, error)
	FindByID(ctx context.Context, id int64) (User, error)
	FindByUsername(ctx context.Context, username string) (User, error)
	FindRoleIDByName(ctx context.Context, name string) (int64, error)
	Create(ctx context.Context, u User) (int64, error)
	UsernameOrEmailExists(ctx context.Context, username, email string) (bool, error)
}
