package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/user/domain"
)

type Repository interface {
	FindAll(ctx context.Context) ([]domain.User, error)
	FindByID(ctx context.Context, id int64) (domain.User, error)
	FindByUsername(ctx context.Context, username string) (domain.User, error)
	FindRoleIDByName(ctx context.Context, name string) (int64, error)
	Create(ctx context.Context, in domain.NewUserInput) (int64, error)
	UsernameOrEmailExists(ctx context.Context, username, email string) (bool, error)
}
