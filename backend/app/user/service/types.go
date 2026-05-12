package service

import (
	"context"

	"github.com/mymikasa/pivot/app/user/domain"
)

type Service interface {
	Login(ctx context.Context, username, password string) (access, refresh string, err error)
	Logout(ctx context.Context) error
	RefreshToken(ctx context.Context, refreshToken string) (access string, err error)
	GetAllUser(ctx context.Context) ([]domain.User, error)
}
