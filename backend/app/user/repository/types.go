package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/user/domain"
)

type Repository interface {
	FindAll(ctx context.Context) ([]domain.User, error)
	FindByUsername(ctx context.Context, username string) (domain.User, error)
}
